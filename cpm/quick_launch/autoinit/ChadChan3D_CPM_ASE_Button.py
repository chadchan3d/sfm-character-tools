# -*- coding: ascii -*-
# SFM Character Preset Manager -- Animation Set Editor Quick Launch bootstrap.
#
# RUN TYPE: AUTOINIT. Deployed as
# <SFM game>/usermod/scripts/sfm/autoinit/ChadChan3D/ChadChan3D_CPM_ASE_Button.py.
# Keep this path stable: Autoinit Manager records disablement by path.
#
# Autoinit runs every startup script in one shared namespace. This bootstrap
# therefore defines no extension code there. It loads the private
# implementation, deployed outside every discovery tree at
# <SFM game>/usermod/scripts/ChadChan3D_CPM/cpm_ase_quick_launch.py, exactly
# once per SFM process into the private module chadchan3d_cpm_ase_quick_launch,
# then asks that module to start, or refresh, its one controller.
#
# Module lifecycle: ABSENT -> LOADING -> READY. READY is permanent until SFM
# exits: the module is never reloaded, replaced or deleted. Running this
# bootstrap again reuses the ready module and controller. If the installed
# implementation bytes change, the bootstrap refuses until SFM is restarted.
#
# The bootstrap keeps its imports and working state local, adds nothing to
# sys.path, and deletes its own function before returning.
#
# To turn the CPM button off, disable this script in Autoinit Manager and
# restart SFM. The Scripts-menu entry keeps opening Character Preset Manager.
#
# (Comments, not a docstring: a module docstring would rebind __doc__ in the
# shared Autoinit namespace.)


def _chadchan3d_cpm_ase_quick_launch_bootstrap_v1():
    import hashlib
    import os
    import sys
    import traceback
    import types

    module_key = "chadchan3d_cpm_ase_quick_launch"
    loader_marker = "cpm-ase-quick-launch-loader-v1"

    def console(sys_module, text):
        try:
            sys_module.stdout.write("[ChadChan3D CPM Quick Launch bootstrap] %s\n" % (text,))
        except Exception:
            pass

    def read_bytes(path):
        handle = None
        try:
            handle = open(path, "rb")
            return handle.read()
        except Exception:
            return None
        finally:
            if handle is not None:
                try:
                    handle.close()
                except Exception:
                    pass

    def classify(entry, types_module, key, marker, impl_path):
        """('ready', sha) | ('loading', None) | (refusal, detail)."""
        try:
            if not isinstance(entry, types_module.ModuleType):
                return ("foreign", "type=%s" % (type(entry).__name__,))
            namespace = entry.__dict__
            if namespace.get("__name__") != key:
                return ("foreign", "name=%r" % (namespace.get("__name__"),))
            if namespace.get("__chadchan3d_cpm_ase_loader__") != marker:
                return ("incompatible", "loader=%r" % (namespace.get("__chadchan3d_cpm_ase_loader__"),))
            if namespace.get("__file__") != impl_path:
                return ("wrong-origin", "file=%r" % (namespace.get("__file__"),))
            build = namespace.get("__chadchan3d_cpm_ase_build_sha256__")
            if not (isinstance(build, str) and len(build) == 64):
                return ("malformed", "build=%r" % (build,))
            state = namespace.get("__chadchan3d_cpm_ase_state__")
            if state == "loading":
                return ("loading", None)
            if state != "ready":
                return ("malformed", "state=%r" % (state,))
            if not callable(namespace.get("bootstrap_request")):
                return ("malformed", "entry point missing")
            return ("ready", build)
        except Exception as exc:
            return ("malformed", "%r" % (exc,))

    impl_path = os.path.normpath(os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(sys.executable)),
        "usermod", "scripts", "ChadChan3D_CPM", "cpm_ase_quick_launch.py",
    )))

    if module_key in sys.modules:
        status, detail = classify(sys.modules.get(module_key), types, module_key, loader_marker, impl_path)
        if status != "ready":
            # LOADING, foreign, incompatible or malformed: never touched.
            console(sys, "outcome=refused code=module-%s detail=%s; restart SFM to "
                         "use the CPM button" % (status, detail))
            return
        source_bytes = read_bytes(impl_path)
        if source_bytes is None:
            code = "installed-unreadable"
        elif hashlib.sha256(source_bytes).hexdigest() != detail:
            code = "installed-build-changed"
        else:
            code = None
        source_bytes = None
        if code is not None:
            # The running controller keeps working; no hot reload.
            console(sys, "outcome=refused code=%s; restart SFM to use the "
                         "installed version" % (code,))
            return
        module = sys.modules[module_key]
    else:
        source_bytes = read_bytes(impl_path)
        if source_bytes is None:
            console(sys, "outcome=refused code=installed-unreadable path=%s" % (impl_path,))
            return
        module = types.ModuleType(str(module_key))
        module.__file__ = impl_path
        module.__chadchan3d_cpm_ase_loader__ = loader_marker
        module.__chadchan3d_cpm_ase_build_sha256__ = str(hashlib.sha256(source_bytes).hexdigest())
        module.__chadchan3d_cpm_ase_state__ = "loading"
        sys.modules[module_key] = module
        try:
            # The same buffer that was hashed; no inherited future flags.
            # eval() runs the exec-mode code object with the module dict as
            # both globals and locals (portable across Python 2.7 and 3).
            code_object = compile(source_bytes, impl_path, "exec", 0, True)
            source_bytes = None
            eval(code_object, module.__dict__, module.__dict__)
            code_object = None
            if sys.modules.get(module_key) is not module:
                raise RuntimeError("private module registration changed during loading")
            if not (module.__dict__.get("__chadchan3d_cpm_ase_state__") == "loading"
                    and callable(module.__dict__.get("bootstrap_request"))):
                raise RuntimeError("private module initialization is incomplete")
            module.__chadchan3d_cpm_ase_state__ = "ready"
        except BaseException as exc:
            # Pre-READY failure: remove only the entry this attempt created,
            # and only while it is still that exact module.
            removed = False
            try:
                if sys.modules.get(module_key) is module:
                    del sys.modules[module_key]
                    removed = True
            except Exception:
                pass
            diagnostics = traceback.format_exc()
            module = None
            source_bytes = None
            code_object = None
            if not isinstance(exc, Exception):
                raise
            exc = None
            try:
                sys.exc_clear()
            except AttributeError:
                pass
            console(sys, "outcome=failed code=load-failed entry_removed=%r\n%s" % (removed, diagnostics))
            return

    try:
        result = module.bootstrap_request()
    except BaseException as exc:
        diagnostics = traceback.format_exc()
        if not isinstance(exc, Exception):
            raise
        exc = None
        try:
            sys.exc_clear()
        except AttributeError:
            pass
        result = "request-raised"
        console(sys, "controller request raised\n%s" % (diagnostics,))
    module = None
    console(sys, "outcome=%s" % (result,))


try:
    _chadchan3d_cpm_ase_quick_launch_bootstrap_v1()
finally:
    try:
        del _chadchan3d_cpm_ase_quick_launch_bootstrap_v1
    except NameError:
        pass
