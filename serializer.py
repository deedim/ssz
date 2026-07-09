from statistics import variance
from enum import IntEnum
from remerkleable.basic import uint8, uint16, uint64, uint128, uint256, byte, boolean, uint32
from remerkleable.complex import Container, Vector, List
from remerkleable.bitfields import Bitvector, Bitlist
from remerkleable.union import Union

BYTES_PER_LENGTH_OFFSET = 4
BITS_PER_BYTE = 8

def _basic_type(value):
    typ = _type_number(value)
    
    if typ == TypeNumber.BOOLEAN:
        return value.to_bytes(1, 'little')
    elif typ == TypeNumber.BYTE:
        return value.to_bytes(1, 'little')
    elif typ == TypeNumber.UINT8:
        return value.to_bytes(1, 'little')
    elif typ == TypeNumber.UINT16:
        return value.to_bytes(2, 'little')
    elif typ == TypeNumber.UINT32:
        return value.to_bytes(4, 'little')
    elif typ == TypeNumber.UINT64:
        return value.to_bytes(8, 'little')
    elif typ == TypeNumber.UINT128:
        return value.to_bytes(16, 'little')
    elif typ == TypeNumber.UINT256:
        return value.to_bytes(32, 'little')

    return b""

# def _is_composite_type(object):
#     return isinstance(object, Container) or isinstance(object, List) or isinstance(objec)

class TypeNumber(IntEnum):
    BOOLEAN = 0
    BYTE = 1
    UINT8 = 1
    UINT16 = 2
    UINT32 = 3
    UINT64 = 4
    UINT128 = 5
    UINT256 = 6
    CONTAINER = 7
    VECTOR = 8
    BIT_VECTOR = 9
    LIST = 10
    BIT_LIST = 11
    UNION = 12

def _type_number(object) -> TypeNumber:
    if isinstance(object, boolean):
        return TypeNumber.BOOLEAN
    elif isinstance(object, byte) or isinstance(object, uint8):
        return TypeNumber.UINT8
    elif isinstance(object, uint16):
        return TypeNumber.UINT16
    elif isinstance(object, uint32):
        return TypeNumber.UINT32
    elif isinstance(object, uint64):
        return TypeNumber.UINT64
    elif isinstance(object, uint128):
        return TypeNumber.UINT128
    elif isinstance(object, uint256):
        return TypeNumber.UINT256
    elif isinstance(object, Container):
        return TypeNumber.CONTAINER
    elif isinstance(object, List):
        return TypeNumber.LIST
    elif isinstance(object, Vector):
        return TypeNumber.VECTOR
    elif isinstance(object, Bitvector):
        return TypeNumber.BIT_VECTOR
    elif isinstance(object, Bitlist):
        return TypeNumber.BIT_LIST
    elif isinstance(object, Union):
        return TypeNumber.UNION
    else:
        raise ValueError(f"Unsupported type: {type(object)}")

def _serialize(object) -> (bool, bytes): # returns (is_variable, serialized_data)
    # print("object: ", object)
    basic_type = _basic_type(object)
    if basic_type:
        return (False, basic_type)
    
    typ = _type_number(object)
    
    # composite type
    
    if typ == TypeNumber.BIT_VECTOR:
        N = len(object)
        array = [0] * ((N + 7) // 8)
        for i, bit in enumerate(object):
            array[i // 8] |= bit << (i % 8)

        return (False, bytes(array))
    elif typ == TypeNumber.BIT_LIST:
        N = len(object)
        array = [0] * ((N // 8) + 1)
        for i, bit in enumerate(object):
            array[i // 8] |= bit << (i % 8)
        array[N // 8] |= 1 << (N % 8)
        return (True, bytes(array))

    flag_is_variable = False    

    if typ in [TypeNumber.CONTAINER, TypeNumber.LIST, TypeNumber.VECTOR]:
        fixed_parts = []
        variable_parts = []
        
        if typ == TypeNumber.CONTAINER:
            items = [getattr(object, field_name) for field_name in object.fields().keys()]
            items_count = len(object.fields())
        else:
            items = list(object)
            items_count = len(object)
        
        for item in items:
            is_variable, serialized = _serialize(item)
            fixed_parts.append(None if is_variable else serialized)
            variable_parts.append(serialized if is_variable else b"")
            if is_variable:
                flag_is_variable = True

        fixed_lengths = [len(part) if part != None else BYTES_PER_LENGTH_OFFSET for part in fixed_parts]
        variable_lengths = [len(part) for part in variable_parts]

        # if typ == TypeNumber.CONTAINER:
        #     print(f"fixed_part =====> {fixed_parts}")
        #     print(f"variable_part =====> {variable_parts}")
        #     print(f"fixed_length =====> {fixed_lengths}")
        #     print(f"variable_length =====> {variable_lengths}")
        
        variable_offsets = [_serialize(uint32(sum(fixed_lengths + variable_lengths[:i])))[1] for i in range(items_count)]
        fixed_parts = [part if part != None else variable_offsets[i] for i, part in enumerate(fixed_parts)]

        # print("fixed_parts: ", fixed_parts)
        # print("variable_parts: ", variable_parts)
        
        # print(variable_parts)
        
        if typ == TypeNumber.LIST:
            return (True, b"".join(fixed_parts) + b"".join(variable_parts))
        
        return (flag_is_variable, b"".join(fixed_parts) + b"".join(variable_parts))
    
    return None

def serialize(object):
    return _serialize(object)[1]
