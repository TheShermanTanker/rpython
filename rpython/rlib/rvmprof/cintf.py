import platform as host_platform
import py
import sys
import shutil
from rpython.tool.udir import udir
from rpython.tool.version import rpythonroot
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib import rthread
from rpython.rlib.objectmodel import we_are_translated
from rpython.config.translationoption import get_translation_config

class VMProfPlatformUnsupported(Exception):
    pass

# vmprof works only on x86 for now
IS_SUPPORTED = False

ROOT = py.path.local(rpythonroot).join('rpython', 'rlib', 'rvmprof')
SRC = ROOT.join('src')
SHARED = SRC.join('shared')
BACKTRACE = SHARED.join('libbacktrace')

def make_eci():
    if make_eci.called:
        raise ValueError("make_eci() should be called at most once")
    #
    compile_extra = ['-DRPYTHON_VMPROF']
    separate_module_files = [
        SHARED.join('symboltable.c'),
        SHARED.join('vmprof_unix.c')
    ]
    if sys.platform.startswith('linux'):
        separate_module_files += [
           BACKTRACE.join('atomic.c'),
           BACKTRACE.join('backtrace.c'),
           BACKTRACE.join('state.c'),
           BACKTRACE.join('elf.c'),
           BACKTRACE.join('dwarf.c'),
           BACKTRACE.join('fileline.c'),
           BACKTRACE.join('mmap.c'),
           BACKTRACE.join('mmapio.c'),
           BACKTRACE.join('posix.c'),
           BACKTRACE.join('sort.c'),
        ]
        _libs = ['dl']
        compile_extra += ['-DVMPROF_UNIX']
        compile_extra += ['-DVMPROF_LINUX']
    elif sys.platform == 'win32':
        compile_extra += ['-DVMPROF_WINDOWS']
        separate_module_files = [SHARED.join('vmprof_win.c')]
        _libs = []
    else:
        # Guessing a BSD-like Unix platform
        compile_extra += ['-DVMPROF_UNIX']
        if sys.platform.startswith('darwin'):
            compile_extra += ['-DVMPROF_APPLE']
        if sys.platform.startswith('freebsd'):
            _libs = ['unwind']
        else:
            _libs = []

    eci_kwds = dict(
        include_dirs = [SRC, SHARED, BACKTRACE],
        includes = ['rvmprof.h','vmprof_stack.h'],
        libraries = _libs,
        separate_module_files = [
            SRC.join('rvmprof.c'),
            SHARED.join('compat.c'),
            SHARED.join('machine.c'),
            SHARED.join('vmp_stack.c'),
            SHARED.join('vmprof_memory.c'),
            SHARED.join('vmprof_common.c'),
            # symbol table already in separate_module_files
        ] + separate_module_files,
        post_include_bits=[],
        compile_extra=compile_extra
        )
    if sys.platform != 'win32':
        eci_kwds['separate_module_files'].append(
            SHARED.join('vmprof_mt.c'),
        )
    make_eci.called = True
    return ExternalCompilationInfo(**eci_kwds), eci_kwds
make_eci.called = False

def configure_libbacktrace_linux():
    bits = 32 if sys.maxsize == 2**31-1 else 64
    # FIXME well, the config generated on x86 seems to work on s390x and ppc
    # vmprof is currently not supported there! we just need to pass compilation
    specific_config = 'config-x86_%d.h' % bits
    config = BACKTRACE.join('config.h')
    shutil.copy(str(BACKTRACE.join(specific_config)), str(config))

def setup():
    if not IS_SUPPORTED:
        raise VMProfPlatformUnsupported
    
    if sys.platform.startswith('linux'):
        configure_libbacktrace_linux()

    eci, eci_kwds = make_eci()
    eci_kwds['compile_extra'].append('-DRPYTHON_LL2CTYPES')
    platform.verify_eci(ExternalCompilationInfo(
                        **eci_kwds))

    vmprof_init = rffi.llexternal("vmprof_init",
                                  [rffi.INT, rffi.DOUBLE, rffi.INT, rffi.INT,
                                   rffi.CCHARP, rffi.INT, rffi.INT],
                                  rffi.CCHARP, compilation_info=eci)
    vmprof_enable = rffi.llexternal("vmprof_enable", [rffi.INT, rffi.INT, rffi.INT],
                                    rffi.INT,
                                    compilation_info=eci,
                                    save_err=rffi.RFFI_SAVE_ERRNO)
    vmprof_disable = rffi.llexternal("vmprof_disable", [], rffi.INT,
                                     compilation_info=eci,
                                     save_err=rffi.RFFI_SAVE_ERRNO)
    vmprof_register_virtual_function = rffi.llexternal(
                                           "vmprof_register_virtual_function",
                                           [rffi.CCHARP, rffi.LONG, rffi.INT],
                                           rffi.INT, compilation_info=eci)
    vmprof_ignore_signals = rffi.llexternal("vmprof_ignore_signals",
                                            [rffi.INT], lltype.Void,
                                            compilation_info=eci,
                                            _nowrapper=True)
    vmprof_get_traceback = rffi.llexternal("vmprof_get_traceback",
                                  [PVMPROFSTACK, llmemory.Address,
                                   rffi.SIGNEDP, lltype.Signed],
                                  lltype.Signed, compilation_info=eci,
                                  _nowrapper=True)

    vmprof_get_profile_path = rffi.llexternal("vmprof_get_profile_path", [rffi.CCHARP, lltype.Signed],
                                              lltype.Signed, compilation_info=eci,
                                              _nowrapper=True)

    vmprof_stop_sampling = rffi.llexternal("vmprof_stop_sampling", [],
                                           rffi.INT, compilation_info=eci,
                                           _nowrapper=True)
    vmprof_start_sampling = rffi.llexternal("vmprof_start_sampling", [],
                                            lltype.Void, compilation_info=eci,
                                            _nowrapper=True)

    return CInterface(locals())


class CInterface(object):
    def __init__(self, namespace):
        for k, v in namespace.iteritems():
            setattr(self, k, v)

    def _freeze_(self):
        return True


# --- copy a few declarations from src/vmprof_stack.h ---

VMPROF_CODE_TAG = 1

VMPROFSTACK = lltype.ForwardReference()
PVMPROFSTACK = lltype.Ptr(VMPROFSTACK)
VMPROFSTACK.become(rffi.CStruct("vmprof_stack_s",
                                ('next', PVMPROFSTACK),
                                ('value', lltype.Signed),
                                ('kind', lltype.Signed)))
# ----------


vmprof_tl_stack = rthread.ThreadLocalField(PVMPROFSTACK, "vmprof_tl_stack")
do_use_eci = rffi.llexternal_use_eci(
    ExternalCompilationInfo(includes=['vmprof_stack.h'],
                            include_dirs = [SRC]))

def enter_code(unique_id):
    do_use_eci()
    s = lltype.malloc(VMPROFSTACK, flavor='raw')
    s.c_next = vmprof_tl_stack.get_or_make_raw()
    s.c_value = unique_id
    s.c_kind = VMPROF_CODE_TAG
    vmprof_tl_stack.setraw(s)
    return s

def leave_code(s):
    if not we_are_translated():
        assert vmprof_tl_stack.getraw() == s
    vmprof_tl_stack.setraw(s.c_next)
    lltype.free(s, flavor='raw')

#
# traceback support

def get_rvmprof_stack():
    return vmprof_tl_stack.get_or_make_raw()
