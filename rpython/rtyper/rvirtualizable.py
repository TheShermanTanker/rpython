from rpython.rtyper.rmodel import inputconst, log
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.rclass import (FieldListAccessor, InstanceRepr)


class VirtualizableInstanceRepr(InstanceRepr):

    def _super(self):
        return super(VirtualizableInstanceRepr, self)

    def __init__(self, rtyper, classdef):
        self._super().__init__(rtyper, classdef)
        classdesc = classdef.classdesc
        if classdesc.get_param('_virtualizable2_'):
            raise Exception("_virtualizable2_ is now called _virtualizable_, "
                            "please rename")
        if classdesc.get_param('_virtualizable_', inherit=False):
            basedesc = classdesc.basedesc
            assert (basedesc is None or
                    basedesc.get_param('_virtualizable_') is None)
            self.top_of_virtualizable_hierarchy = True
            self.accessor = FieldListAccessor()
        else:
            self.top_of_virtualizable_hierarchy = False

    def _setup_repr_llfields(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_token', llmemory.GCREF))
        return llfields

    def _setup_repr(self):
        if self.top_of_virtualizable_hierarchy:
            hints = {'virtualizable_accessor': self.accessor}
            llfields = self._setup_repr_llfields()
            if llfields:
                self._super()._setup_repr(llfields, hints=hints)
            else:
                self._super()._setup_repr(hints = hints)
            vfields = self.classdef.classdesc.get_param('_virtualizable_')
            self.my_redirected_fields = self._parse_field_list(
                vfields, self.accessor, hints)
        else:
            self._super()._setup_repr()
            # ootype needs my_redirected_fields even for subclass. lltype does
            # not need it, but it doesn't hurt to have it anyway
            self.my_redirected_fields = self.rbase.my_redirected_fields

    def hook_access_field(self, vinst, cname, llops, flags):
        # if not flags.get('access_directly'):
        if self.my_redirected_fields.get(cname.value):
            cflags = inputconst(lltype.Void, flags)
