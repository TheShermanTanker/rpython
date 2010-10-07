import conditions as cond
from pypy.rlib.rmmap import alloc
from pypy.rpython.lltypesystem import lltype, rffi

class ARMv7Builder(object):

    def __init__(self):
        self._data = alloc(1024)
        self._pos = 0

    def _encode_imm(self, imm):
        u = 1
        if imm < 0:
            u = 0
            imm = -imm
        return u, imm

    def LDR_ri(self, rt, rn, imm=0, cond=cond.AL):
        #  XXX W and P bits are not encoded yet
        p = 1
        w = 0
        u, imm = self._encode_imm(imm)
        self.write32(cond << 28
                        | 0x1 << 26
                        | (p & 0x1) << 24
                        | (u & 0x1) << 23
                        | (w & 0x1) << 21
                        | 0x1 << 20
                        | (rn & 0xF) << 16
                        | (rt & 0xF) << 12
                        | (imm & 0xFFF))

    def ADD_ri(self, rt, rn, imm, cond=cond.AL):
        # XXX S bit
        self.write32(cond << 28
                        | 2 << 24
                        | 8 << 20
                        | (rn & 0xF) << 16
                        | (rt & 0xF) << 12
                        | (imm & 0xFFF))

    def SUB_ri(self, rd, rn, imm=0, cond=cond.AL, s=0):
        self.write32(cond << 28
                        | 9 << 22
                        | (s & 0x1) << 20
                        | (rn & 0xF) << 16
                        | (rd & 0xF) << 12
                        | (imm & 0xFFF))


    def MOV_rr(self, rd, rm, cond=cond.AL, s=0):
        self.write32(cond << 28
                    | 0xD << 21
                    | (s & 0x1) << 20
                    | (rd & 0xFF) << 12
                    | (rm & 0xFF))

    def MOV_ri(self, rt, imm=0, cond=cond.AL):
        # XXX Check the actual allowed size for imm
        # XXX S bit
        self.write32(cond << 28
                    | 0x3 << 24
                    | 0xA << 20
                    #| 0x0 << 16
                    | (rt & 0xF) << 12
                    | (imm & 0xFFF))

    def STR_ri(self, rt, rn, imm=0, cond=cond.AL):
        #  XXX W and P bits are not encoded yet
        p = 1
        w = 0
        u, imm = self._encode_imm(imm)
        self.write32(cond << 28
                    | 0x1 << 26
                    | (p & 0x1) << 24
                    | (u & 0x1) << 23
                    | (w & 0x1) << 21
                    | (rn & 0xF) << 16
                    | (rt & 0xF) << 12
                    | (imm & 0xFFF))

    def ASR_ri(self, rd, rm, imm=0, cond=cond.AL, s=0):
        self.write32(cond << 28
                    | 0xD << 21
                    | (s & 0x1) << 20
                    | (rd & 0xF) << 12
                    | (imm & 0x1F) << 7
                    | 0x4 << 4
                    | (rm & 0xF))

    #XXX encode shifttype correctly
    def ORR_rr(self, rd, rn, rm, imm=0, cond=cond.AL, s=0, shifttype=0):
        self.write32(cond << 28
                    | 0x3 << 23
                    | (s & 0x1) << 20
                    | (rn & 0xFF) << 16
                    | (rd & 0xFF) << 12
                    | (imm & 0x1F) << 7
                    | (shifttype & 0x3) << 5
                    | (rm & 0xFF))

    def PUSH(self, regs, cond=cond.AL):
        instr = cond << 28 | 0x92D << 16
        for reg in regs:
            instr |= 0x1 << reg
        self.write32(instr)

    def write32(self, word):
        self.writechar(chr(word & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 24) & 0xFF))

    def writechar(self, char):
        self._data[self._pos] = char
        self._pos += 1

    def baseaddr(self):
        return rffi.cast(lltype.Signed, self._data)


