"""Finite lossless evidence frames; standard-library only, no project imports."""
import gzip
import hashlib
import json
import os
import struct
import time
import zlib

RAW_BYTES = 192 * 1024 * 1024
COMPRESSED_BYTES = 3 * 1024 * 1024
FRAME_RAW_BYTES = 193 * 1024 * 1024
TERMINAL_RESERVE = 524288
MAX_RECORDS = 8192

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode() + b"\n"

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def valid_name(name):
    return (type(name) is str and name.isascii() and 0 < len(name) <= 96
            and not name.startswith("/") and "\\" not in name
            and all(p not in ("", ".", "..") for p in name.split("/")))

def compressed_upper(raw_bytes, records=1):
    if type(raw_bytes) is not int or raw_bytes < 0 or type(records) is not int or records < 1:
        raise ValueError("COMPRESSED_BOUND_DOMAIN")
    # Default zlib stored-block worst case plus frame headers and sync flushes.
    return raw_bytes + raw_bytes // 1000 + records * 1024

class Evidence:
    def __init__(self, folder):
        folder.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.folder = folder
        self.file = (folder / "records.gz").open("xb")
        self.state = "UNKNOWN"
        self.total = 0
        self.rows = []
        self.prefix = ""
        self.names = set()
        self.gz = gzip.GzipFile(filename="", mode="wb", compresslevel=9, mtime=0,
                                fileobj=self.file)
        self.state = "LIVE"

    @property
    def compressed(self):
        return self.file.tell()

    def write(self, name, value, terminal=False):
        if self.state != "LIVE":
            raise ValueError("EVIDENCE_NOT_LIVE_NO_RETRY")
        full = self.prefix + name
        # Ordinary writes leave a slot for result.json or failure.json.
        # A count veto must not itself consume the terminal evidence slot.
        limit = MAX_RECORDS if terminal else MAX_RECORDS - 1
        if not valid_name(full) or full in self.names or len(self.names) >= limit:
            raise ValueError("EVIDENCE_NAME_COUNT")
        raw = canonical(value)
        reserve = 0 if terminal else TERMINAL_RESERVE
        if self.total + len(raw) + reserve > RAW_BYTES:
            raise ValueError("RAW_CAP_NO_TRUNCATION")
        if self.compressed + compressed_upper(len(raw)) + reserve + 32 > COMPRESSED_BYTES:
            raise ValueError("COMPRESSED_CAP_NO_TRUNCATION")
        began = time.monotonic()
        row = dict(name=full, bytes=len(raw), sha256=digest(raw), write_flush_seconds=0.0)
        if len(canonical(row)) > 256:
            raise ValueError("JOURNAL_ROW_BOUND")
        try:
            self.state = "UNKNOWN"
            header = struct.pack(">HI", len(full), len(raw)) + full.encode("ascii")
            if self.gz.write(header + raw) != len(header) + len(raw):
                raise OSError("SHORT_GZIP_WRITE")
            self.gz.flush(zlib.Z_SYNC_FLUSH)
            self.file.flush()
            os.fsync(self.file.fileno())
            if self.file.tell() > COMPRESSED_BYTES:
                raise ValueError("PHYSICAL_COMPRESSED_CAP")
            self.total += len(raw)
            self.names.add(full)
            row["write_flush_seconds"] = time.monotonic() - began
            if len(canonical(row)) > 256:
                raise ValueError("JOURNAL_ROW_BOUND")
            self.rows.append(row)
            self.state = "LIVE"
            return row
        except BaseException:
            self.state = "UNKNOWN"
            # Preserve the physical prefix; suppress implicit gzip finalization after
            # an uncertain write. The regular file is not a held native capability.
            self.gz.fileobj = None
            raise

    def finish(self):
        if self.state != "LIVE":
            raise ValueError("EVIDENCE_FINISH_NO_RETRY")
        self.state = "UNKNOWN"
        self.gz.close()
        self.file.flush()
        os.fsync(self.file.fileno())
        if self.file.tell() > COMPRESSED_BYTES:
            raise ValueError("PHYSICAL_COMPRESSED_CAP")
        self.file.close()
        self.state = "CLOSED"

def decode(encoded):
    """Bounded independent complete decoder; exact raw bytes, no JSON coercion."""
    if len(encoded) > COMPRESSED_BYTES:
        raise ValueError("ENCODED_CAP")
    obj = zlib.decompressobj(16 + zlib.MAX_WBITS)
    raw = obj.decompress(encoded, FRAME_RAW_BYTES + 1)
    if len(raw) > FRAME_RAW_BYTES or not obj.eof or obj.unused_data or obj.unconsumed_tail:
        raise ValueError("GZIP_BOUND_CRC_EOF")
    records = {}
    offset = 0
    total = 0
    while offset < len(raw):
        if len(raw) - offset < 6 or len(records) >= MAX_RECORDS:
            raise ValueError("FRAME_HEADER_COUNT")
        name_length, data_length = struct.unpack(">HI", raw[offset:offset + 6])
        offset += 6
        if not 0 < name_length <= 96 or data_length > RAW_BYTES:
            raise ValueError("FRAME_LENGTH")
        end = offset + name_length + data_length
        if end > len(raw):
            raise ValueError("FRAME_TRUNCATED")
        name = raw[offset:offset + name_length].decode("ascii")
        offset += name_length
        if not valid_name(name) or name in records:
            raise ValueError("FRAME_NAME_DUPLICATE")
        total += data_length
        if total > RAW_BYTES:
            raise ValueError("DECODED_RAW_CAP")
        records[name] = raw[offset:end]
        offset = end
    return records
