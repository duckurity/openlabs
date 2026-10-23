from pathlib import Path


def varint(value):
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def key(number, wire_type):
    return varint((number << 3) | wire_type)


def int_field(number, value):
    return key(number, 0) + varint(value)


def bytes_field(number, value):
    return key(number, 2) + varint(len(value)) + value


def string_field(number, value):
    return bytes_field(number, value.encode())


def message(parts):
    return b"".join(parts)


def string_descriptor(name, number, json_name):
    return message(
        [
            string_field(1, name),
            int_field(3, number),
            int_field(4, 1),
            int_field(5, 9),
            string_field(10, json_name),
        ]
    )


def message_descriptor(name, fields):
    return message([string_field(1, name)] + [bytes_field(2, field) for field in fields])


get_request = message_descriptor(
    "GetDocumentRequest",
    [
        string_descriptor("tenant_id", 1, "tenantId"),
        string_descriptor("doc_id", 2, "docId"),
    ],
)

reply = message_descriptor(
    "DocumentReply",
    [
        string_descriptor("tenant_id", 1, "tenantId"),
        string_descriptor("doc_id", 2, "docId"),
        string_descriptor("title", 3, "title"),
        string_descriptor("body", 4, "body"),
        string_descriptor("classification", 5, "classification"),
    ],
)

http_rule = message([string_field(2, "/api/v1/tenants/{tenant_id}/documents/{doc_id}")])
method_options = message([bytes_field(72295728, http_rule)])
method = message(
    [
        string_field(1, "GetDocument"),
        string_field(2, ".tenantexchange.GetDocumentRequest"),
        string_field(3, ".tenantexchange.DocumentReply"),
        bytes_field(4, method_options),
    ]
)
service = message([string_field(1, "Documents"), bytes_field(2, method)])
file_descriptor = message(
    [
        string_field(1, "tenantexchange.proto"),
        string_field(2, "tenantexchange"),
        string_field(3, "google/api/annotations.proto"),
        bytes_field(4, get_request),
        bytes_field(4, reply),
        bytes_field(6, service),
        string_field(12, "proto3"),
    ]
)

out = Path("public_docs/descriptors/tenantexchange.protoset")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(bytes_field(1, file_descriptor))
