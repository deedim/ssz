from typing import Any
from remerkleable.basic import uint8, uint16, uint32, uint64, uint128, uint256, boolean, byte
from remerkleable.complex import Container, Vector, List
from remerkleable.bitfields import Bitvector, Bitlist

BYTES_PER_LENGTH_OFFSET = 4
BITS_PER_BYTE = 8

class Transaction(Container):
    from_addr: Vector[uint8, 20]  # fixed
    to_addr: Vector[uint8, 20]  # fixed
    value: uint64  # fixed
    data: List[uint8, 1024]  # variable!

class Block(Container):
    slot: uint64  # fixed
    transactions: List[Transaction, 16]  # variable!
    state_root: Vector[uint8, 32]  # fixed

def _deserialize_basic(typ, buf: bytes) -> Any | None:
    if issubclass(typ, boolean):
        assert len(buf) == 1
        return boolean.decode_bytes(buf)
    elif issubclass(typ, byte):
        assert len(buf) == 1
        return byte.decode_bytes(buf)
    elif issubclass(typ, uint8):
        assert len(buf) == 1
        return uint8.decode_bytes(buf)
    elif issubclass(typ, uint16):
        assert len(buf) == 2
        return uint16.decode_bytes(buf)
    elif issubclass(typ, uint32):
        assert len(buf) == 4
        return uint32.decode_bytes(buf)
    elif issubclass(typ, uint64):
        assert len(buf) == 8
        return uint64.decode_bytes(buf)
    elif issubclass(typ, uint128):
        assert len(buf) == 16
        return uint128.decode_bytes(buf)
    elif issubclass(typ, uint256):
        assert len(buf) == 32
        return uint256.decode_bytes(buf)
    
    return None
    

def _deserialize_fixed_type(typ, buf: bytes) -> Any | None:
    basic = _deserialize_basic(typ, buf)
    if basic is not None:
        return basic
    
    if issubclass(typ, Container):
        pointer = 0
        kwargs = {}
        for field_name in typ.fields(): # items
            field_type = typ.__annotations__[field_name]
            type_length = field_type.type_byte_length()
            kwargs[field_name] = _deserialize_fixed_type(field_type, buf[pointer:pointer + type_length])
            pointer += type_length
        return typ(**kwargs)
    
    if issubclass(typ, Vector):
        pointer = 0
        elements = []
        type_length = typ.element_cls().type_byte_length()
        for _ in range(typ.vector_length()):
            elements.append(_deserialize_fixed_type(typ.element_cls(), buf[pointer:pointer + type_length]))
            pointer += type_length
        return typ(*elements)
    
    if issubclass(typ, Bitvector):
        length = typ.vector_length()
        arr = [False] * length
        for bit_index in range(length):
            arr[bit_index] = bool(buf[bit_index // BITS_PER_BYTE] & (1 << (bit_index % BITS_PER_BYTE)))
        return typ(*arr)

    return None

def _calculate_sizes(offsets: list[int], buf_length: int) -> list[int]:
    sizes = []
    if len(offsets) == 1:
        sizes.append(buf_length - offsets[0])
    else:
        for i in range(len(offsets) - 1):
            sizes.append(offsets[i + 1] - offsets[i])
        sizes.append(buf_length - offsets[-1])
    return sizes
    
def _deserialize(typ, buf: bytes) -> Any:
    pointer = 0
    kwargs = {}
    offsets = []
    buf_length = len(buf)
    
    if typ.is_fixed_byte_length():
        return _deserialize_fixed_type(typ, buf)
    
    if issubclass(typ, Container):
        # Container
        variable_fields = []
        for field_name in typ.fields():
            field_type = typ.__annotations__[field_name]
            if field_type.is_fixed_byte_length():
                type_length = field_type.type_byte_length()
                kwargs[field_name] = _deserialize_fixed_type(field_type, buf[pointer:pointer + type_length])
                pointer += type_length
            else:
                variable_fields.append((field_name, field_type))
                offsets.append(int.from_bytes(buf[pointer: pointer + BYTES_PER_LENGTH_OFFSET], 'little'))
                pointer += BYTES_PER_LENGTH_OFFSET
        
        if len(offsets) == 0:
            return typ(**kwargs)
            
        sizes = _calculate_sizes(offsets, buf_length)
        
        for (field_name, field_type), offset, size in zip(variable_fields, offsets, sizes):
            kwargs[field_name] = _deserialize(field_type, buf[offset:offset + size])
    
        return typ(**kwargs)

    elif issubclass(typ, Vector) or issubclass(typ, List):
        elements = []
        is_fixed = typ.element_cls().is_fixed_byte_length()

        if issubclass(typ, Vector):
            length = typ.vector_length()
        elif is_fixed:
            length = buf_length // typ.element_cls().type_byte_length()
        else:
            length = int.from_bytes(buf[:4], 'little') // BYTES_PER_LENGTH_OFFSET

        if is_fixed:
            type_length = typ.element_cls().type_byte_length()
            for _ in range(length):
                elements.append(_deserialize_fixed_type(typ.element_cls(), buf[pointer:pointer + type_length]))
                pointer += type_length
        else:
            for _ in range(length):
                offset = int.from_bytes(buf[pointer:pointer + BYTES_PER_LENGTH_OFFSET], 'little')
                offsets.append(offset)
                pointer += BYTES_PER_LENGTH_OFFSET
            
            sizes = _calculate_sizes(offsets, buf_length)
        
            for offset, size in zip(offsets, sizes):
                elements.append(_deserialize(typ.element_cls(), buf[offset:offset + size]))
        return typ(*elements)
    
    elif issubclass(typ, Bitlist):
        last_byte = buf[-1]
        sentinel_index = -1
        for i in range(BITS_PER_BYTE - 1, -1, -1):
            if last_byte & (1 << i):
                sentinel_index = i
                break
        assert sentinel_index != -1
        length = (len(buf) * BITS_PER_BYTE - BITS_PER_BYTE + sentinel_index)
        arr = [False] * length
        for bit_index in range(length):
            arr[bit_index] = bool(buf[bit_index // BITS_PER_BYTE] & (1 << (bit_index % BITS_PER_BYTE)))
        return typ(*arr)

    assert False

def deserialize(typ: Any, buf: bytes) -> Any:
    return _deserialize(typ, buf)
