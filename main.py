from serializer import serialize
from deserializer import deserialize

from remerkleable.basic import uint8, uint16, uint64, uint128, uint256, byte, boolean, uint32
from remerkleable.complex import Container, Vector, List
from remerkleable.bitfields import Bitvector, Bitlist
from remerkleable.union import Union

def print_bytes_hex(bs):
    return " ".join(f"0x{byte:02X}" for byte in bs)

def _print_bytes_bit(bs):
    return " ".join(f"{byte:08b}" for byte in bs)

######################## encode

class Container1(Container):
    id: uint32
    data: Bitvector[10]
    tag: uint32
    
value = Container1(
    id=1,
    data=[1, 1, 1, 0, 1, 0, 1, 0, 1, 0],
    tag=2
)

encoded_ = serialize(value)
print(print_bytes_hex(encoded_))
encoded = value.encode_bytes()
print(print_bytes_hex(encoded))

print(encoded_ == encoded)

######################## decode

class ContainerB(Container):
    x: uint64
    y: List[uint64, 16]
    z: uint64

class ContainerA(Container):
    a: uint64
    b: Vector[ContainerB, 3]
    c: uint64

container_a = ContainerA(
    a=uint64(123456789),
    b=[ContainerB(
        x=uint64(123456789),
        y=List[uint64, 16](*[i for i in range(16)]),
        z=uint64(987654321)
    ) for _ in range(3)],
    c=uint64(987654321)
)

tx1 = Transaction(
    from_addr=Vector[uint8, 20](*[0xAA] * 20),
    to_addr=Vector[uint8, 20](*[0xBB] * 20),
    value=uint64(1000),
    data=List[uint8, 1024](*[0x01, 0x02, 0x03])  # 3 bytes
)
tx2 = Transaction(
    from_addr=Vector[uint8, 20](*[0xCC] * 20),
    to_addr=Vector[uint8, 20](*[0xDD] * 20),
    value=uint64(2000),
    data=List[uint8, 1024](*[0x04, 0x05])  # 2 bytes
)
block = Block(
    slot=uint64(12345),
    transactions=List[Transaction, 16](tx1, tx2),
    state_root=Vector[uint8, 32](*[0x00] * 32)
)

class Attestation(Container):
    aggregation_bits: Bitlist[2048]  # variable
    data: Vector[uint8, 128]  # fixed
    signature: Vector[uint8, 96]  # fixed

class AttestationData(Container):
    slot: uint64
    index: uint64
    beacon_block_root: Vector[uint8, 32]
    source_epoch: uint64
    target_epoch: uint64

class ComplexAttestation(Container):
    att_data: AttestationData  # fixed
    aggregation_bits: Bitlist[2048]  # variable
    custody_bits: Bitvector[256]  # fixed

att_data = AttestationData(
    slot=uint64(100),
    index=uint64(5),
    beacon_block_root=Vector[uint8, 32](*[0xAB] * 32),
    source_epoch=uint64(10),
    target_epoch=uint64(11)
)

# Bitlist: [True, False, True, True, False, ...] 100
bits = [i % 3 == 0 for i in range(100)]
agg_bits = Bitlist[2048](*bits)

# Bitvector: 256 bits
custody = Bitvector[256](*[i % 2 == 0 for i in range(256)])

complex_att = ComplexAttestation(
    att_data=att_data,
    aggregation_bits=agg_bits,
    custody_bits=custody
)

print(deserialize(ComplexAttestation, complex_att.encode_bytes()))
print("===" * 50)
print(complex_att)
print("===" * 50)

# print(complex_att)
encoded = complex_att.encode_bytes()
# print(ComplexAttestation.decode_bytes(encoded))

# print(deserialize(ComplexAttestation, complex_att.encode_bytes()).encode_bytes())
assert deserialize(ComplexAttestation, complex_att.encode_bytes()).encode_bytes() == encoded