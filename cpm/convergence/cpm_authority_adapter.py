# -*- coding: utf-8 -*-
"""CPM-owned canonical authority adapter (CPM convergence Step 2a).

Sits between the existing CPM semantic model and the Step 1
``cpm_compat_v1`` projection:

    CPM semantic model (prod_scope / semantic_snapshot_*; unchanged)
        -> CpmAuthorityAdapter   (this module; provider-shaped facade)
        -> cpm_compat_v1 projection + exact-answer interpreter (Step 1)
        -> canonical broker (sfm_master_authority_productionized.runtime)

This module:

* locates the canonical package with the same ``sys.executable``-derived
  MAINMENU formula as the qualified production Normalizer, and verifies
  origin, module identity, API and build before obtaining the one broker
  through ``runtime.get_broker(...)``;
* presents only ``generation_descriptor()`` and ``query_many(literals)``,
  which is what ``semantic_snapshot_for_model_row()`` consumes;
* performs every semantic read as one bounded operation (acquire or reuse,
  lease, validate, interpret, release, clear references) and retains no
  lease, view, provider or result object afterwards;
* establishes authority health from successful canonical admission plus
  validation of the requested view (reviewer decision R3). No whole-Master
  count thresholds are used;
* offers an expected-generation freshness check for later wiring.

Any failure in that chain raises ``CpmAuthorityUnavailable`` (or its
subclass ``CpmGenerationMismatch``). A failure never becomes MasterUnknown,
absence or Review input.

Not used, directly or indirectly: G18AN's development sidecar discovery,
its TXT provider, its ``get_semantic_provider()`` singleton, or any
fallback. Nothing here is wired into a runnable CPM yet (that is Step 2b).

Runtime: Python 2.7.5 (embedded SFM) and Python 3.
"""
import os
import sys

import cpm_compat_v1_projection as cpm

try:
    _TEXT = unicode  # noqa: F821 -- Python 2
except NameError:  # Python 3
    _TEXT = str


PACKAGE_NAME = "sfm_master_authority_productionized"
RUNTIME_MODULE_NAME = PACKAGE_NAME + ".runtime"
# Pinned literals, deliberately not read from the loaded package: a stale or
# foreign build would otherwise agree with itself.
EXPECTED_API_VERSION = "1.0.0-b2a"
EXPECTED_BUILD_ID = "package-boundary-corrected-2026-09-22"
# Same components as the qualified Normalizer's _authority_locate_mainmenu_dir(): the internal
# library directory, outside the Scripts-menu tree (SFM lists every .py under it as a menu item).
MAINMENU_RELATIVE_PARTS = ("usermod", "scripts", "SFM Character Tools")

# Same value as G18AN PROD_SEMANTIC_POLICY; part of the compatibility identity.
CPM_SEMANTIC_POLICY_REVISION = u"master-category-operation-scope-v1"
CPM_PROVIDER_KIND = u"canonical-broker-cpm-compat-v1"
# Advisory only (G18AN PROD_MASTER_REVIEW_WARNING_THRESHOLD). Never affects health.
ADVISORY_UNRECOGNIZED_THRESHOLD = 20

HEALTH_HEALTHY = u"healthy"
HEALTH_UNAVAILABLE = u"unavailable"


class CpmAuthorityUnavailable(Exception):
    """The canonical authority could not be established for this request.
    ``reason`` is a stable machine-readable code. Never a healthy absence."""

    def __init__(self, reason, message):
        Exception.__init__(self, message)
        self.reason = reason


class CpmGenerationMismatch(CpmAuthorityUnavailable):
    """The current authority generation is not the expected one."""


# ---------------------------------------------------------------------------
# Part A -- canonical bootstrap
# ---------------------------------------------------------------------------

def locate_mainmenu_dir(executable=None):
    """MAINMENU directory derived only from ``sys.executable`` (never
    __file__, the CWD or a repository path). Identical formula to the
    qualified Normalizer and to the package's own
    ``bootstrap.bootstrap_import_path()``."""
    exe = executable if executable is not None else sys.executable
    game_root = os.path.dirname(os.path.abspath(exe))
    return os.path.join(game_root, *MAINMENU_RELATIVE_PARTS)


def _fail(reason, message):
    raise CpmAuthorityUnavailable(reason, message)


def verify_canonical_runtime(mainmenu_dir):
    """Verify the already-importable canonical runtime. Returns the runtime
    module. ``mainmenu_dir`` is the directory expected to contain the
    package; production passes ``locate_mainmenu_dir()``."""
    try:
        __import__(RUNTIME_MODULE_NAME)
        from sfm_master_authority_productionized import bootstrap as authority_bootstrap
    except Exception as exc:
        _fail(u"runtime-import-failed", "canonical runtime import failed: %r" % (exc,))
    runtime = sys.modules.get(RUNTIME_MODULE_NAME)
    if runtime is None or getattr(runtime, "__name__", None) != RUNTIME_MODULE_NAME:
        _fail(u"module-identity", "canonical runtime is not loaded under %r" % (RUNTIME_MODULE_NAME,))

    if authority_bootstrap.bootstrap_import_path() != locate_mainmenu_dir():
        _fail(u"bootstrap-formula-diverged",
              "package bootstrap_import_path() diverged from the sys.executable-derived formula")

    try:
        runtime.assert_expected_origin(os.path.join(mainmenu_dir, PACKAGE_NAME))
    except Exception as exc:
        _fail(u"origin-mismatch", "canonical package origin check failed: %s" % (exc,))

    if getattr(runtime, "RUNTIME_API_VERSION", None) != EXPECTED_API_VERSION:
        _fail(u"api-mismatch", "runtime API %r, expected %r"
              % (getattr(runtime, "RUNTIME_API_VERSION", None), EXPECTED_API_VERSION))
    if not hasattr(runtime, "RUNTIME_BUILD_ID"):
        _fail(u"build-missing", "runtime has no RUNTIME_BUILD_ID")
    if runtime.RUNTIME_BUILD_ID != EXPECTED_BUILD_ID:
        _fail(u"build-mismatch", "runtime build %r, expected %r" % (runtime.RUNTIME_BUILD_ID, EXPECTED_BUILD_ID))
    if not runtime.is_canonical():
        _fail(u"module-identity", "runtime did not load as the canonical module object")
    return runtime


def canonical_bootstrap(mainmenu_dir=None, is_main_thread_fn=None):
    """Establish the one canonical broker. Returns ``(broker, identity)``,
    where ``identity`` is detached text-only data. ``mainmenu_dir`` defaults
    to the sys.executable formula; it is overridable only so offline
    qualification can point at a checked-in package copy."""
    target = mainmenu_dir if mainmenu_dir is not None else locate_mainmenu_dir()
    if target not in sys.path:
        sys.path.insert(0, target)
    runtime = verify_canonical_runtime(target)
    try:
        broker = runtime.get_broker(
            expected_api_version=EXPECTED_API_VERSION,
            expected_build_id=EXPECTED_BUILD_ID,
            is_main_thread_fn=is_main_thread_fn,
        )
    except Exception as exc:
        _fail(u"broker-unavailable", "canonical get_broker() failed: %r" % (exc,))
    identity = {
        "runtime_api_version": _TEXT(runtime.RUNTIME_API_VERSION),
        "runtime_build_id": _TEXT(runtime.RUNTIME_BUILD_ID),
        "runtime_module": _TEXT(RUNTIME_MODULE_NAME),
    }
    return broker, identity


def default_shipped_root():
    """Canonical published-sidecar location, from the package's own
    bootstrap module (not G18AN's development discovery)."""
    from sfm_master_authority_productionized import bootstrap as authority_bootstrap
    return authority_bootstrap.installed_authority_root()


def open_canonical_authority(master_path, mainmenu_dir=None, shipped_root=None, is_main_thread_fn=None):
    broker, identity = canonical_bootstrap(mainmenu_dir, is_main_thread_fn)
    return CpmAuthorityAdapter(
        broker, master_path,
        shipped_root=shipped_root if shipped_root is not None else default_shipped_root(),
        runtime_identity=identity,
    )


# ---------------------------------------------------------------------------
# Parts B-H -- provider-shaped adapter
# ---------------------------------------------------------------------------

def _detach(exc):
    """(class, reason, message) triple; drops traceback and context."""
    return (type(exc), exc.reason, _TEXT(exc))


def _classify_broker_error(exc):
    name = type(exc).__name__
    if name == "AuthorityChangedDuringAcquisition":
        return CpmGenerationMismatch(u"generation-mismatch", "authority generation changed: %s" % (exc,))
    return CpmAuthorityUnavailable(u"acquisition-failed:%s" % (name,), "canonical acquisition failed: %s" % (exc,))


class CpmAuthorityAdapter(object):
    """Provider-shaped facade over the canonical broker.

    State kept between calls is detached text/int data only: the broker
    reference (the process-wide canonical singleton), the Master path, the
    published root, the pinned generation SHA and simple counters. No lease,
    view, coverage, payload or provider object is ever stored on the
    instance."""

    def __init__(self, broker, master_path, shipped_root, runtime_identity=None,
                 semantic_policy_revision=CPM_SEMANTIC_POLICY_REVISION):
        self._broker = broker
        self._master_path = master_path
        self._shipped_root = shipped_root
        self._runtime_identity = dict(runtime_identity or {})
        self._policy = _TEXT(semantic_policy_revision)
        self._pinned_sha = None
        self._operation_count = 0

    # -- generation pinning --------------------------------------------------

    def pinned_generation(self):
        return self._pinned_sha

    def _pin(self):
        if self._pinned_sha is None:
            try:
                obs = self._broker.observe(self._master_path)
            except Exception as exc:
                raise CpmAuthorityUnavailable(u"observation-failed", "Master observation failed: %r" % (exc,))
            self._pinned_sha = _TEXT(obs.sha256)
        return self._pinned_sha

    # -- provider-shaped interface ------------------------------------------

    def generation_descriptor(self):
        """Detached descriptor for scope construction. Pins the generation on
        first use; every later ``query_many`` is acquired with
        ``expected_generation`` equal to this pin, so the descriptor and the
        answers always describe the same generation or the query fails.
        ``valid`` means "canonical runtime verified and generation pinned";
        authority health itself is proven only by a completed bounded read.
        No whole-Master count fields are provided."""
        sha = self._pin()
        return {
            "provider_contract": cpm.CPM_PROVIDER_CONTRACT,
            "provider_kind": CPM_PROVIDER_KIND,
            "source_sha256": sha,
            "fold_policy": cpm.CPM_FOLD_POLICY,
            "provider_generation": cpm.CPM_DESCRIPTOR_PROVIDER_GENERATION,
            "projection_contract": cpm.PAYLOAD_CONTRACT,
            "consumer_kind": _TEXT(cpm.CONSUMER_KIND),
            "semantic_policy_revision": self._policy,
            "runtime_api_version": self._runtime_identity.get("runtime_api_version"),
            "runtime_build_id": self._runtime_identity.get("runtime_build_id"),
            "valid": True,
        }

    def query_many(self, literals):
        """Exact G18AN-shaped answers for exact live literals, pinned to the
        descriptor's generation. Raises CpmAuthorityUnavailable on any
        failure; never returns synthetic absence."""
        answers, _ = self._bounded_read(literals, self._pin())
        return answers

    # -- bounded operation ---------------------------------------------------

    def _bounded_read(self, literals, expected_sha):
        """acquire/reuse -> lease -> validate -> interpret -> release ->
        clear. Failures are re-raised as fresh exceptions built from
        (class, reason, message) only, outside any handler, so no traceback
        or exception context can keep a view, lease or broker frame alive."""
        literal_list = [cpm._to_text(item, "literal") for item in literals]
        folds = cpm.request_folds_for_literals(literal_list)
        specs = cpm.make_request_specs(folds)
        self._operation_count += 1
        failure = None
        view = None
        try:
            views = self._broker.acquire_or_reuse_views(
                self._master_path, specs, shipped_root=self._shipped_root,
                expected_generation=expected_sha,
            )
            view = views.get(cpm.CONSUMER_KIND) if isinstance(views, dict) else None
            views = None
        except Exception as exc:
            failure = _detach(_classify_broker_error(exc))
        if failure is None and view is None:
            failure = (CpmAuthorityUnavailable, u"view-missing", "broker returned no cpm_compat_v1 view")
        if failure is not None:
            view = None
            raise failure[0](failure[1], failure[2])

        lease = None
        try:
            lease = self._broker.lease_view(view)
        except Exception as exc:
            failure = (CpmAuthorityUnavailable, u"lease-refused", "view lease refused: %r" % (exc,))
        if failure is not None:
            view = None
            raise failure[0](failure[1], failure[2])

        result = None
        try:
            result = self._materialize(view, folds, literal_list, expected_sha)
        except CpmAuthorityUnavailable as exc:
            failure = _detach(exc)
        except Exception as exc:
            failure = (CpmAuthorityUnavailable, u"projection-invalid", "cpm_compat_v1 validation failed: %s" % (exc,))
        release_failure = self._release(lease)
        lease = None
        view = None
        if failure is None:
            failure = release_failure
        if failure is not None:
            result = None
            raise failure[0](failure[1], failure[2])
        return result

    def _materialize(self, view, folds, literal_list, expected_sha):
        token = getattr(view, "authorization", None)
        if token is None or not token.is_valid():
            raise CpmAuthorityUnavailable(u"authorization-invalid", "view authorization is not valid")
        token.require_valid("CPM semantic read")
        sha = _TEXT(view.semantic_generation.master_sha256)
        if sha != expected_sha:
            raise CpmGenerationMismatch(u"generation-mismatch",
                                        "view generation %s differs from expected %s" % (sha, expected_sha))
        cpm.validate_view(view, folds)
        answers = cpm.interpret_exact_answers(literal_list, view.payload)
        if sorted(answers.keys()) != sorted(set(literal_list)):
            raise CpmAuthorityUnavailable(u"interpretation-incomplete", "not every literal was interpreted")
        provenance = {
            "compatibility_identity": cpm.compatibility_identity(sha, self._policy),
            "provider_capture": dict((k, v) for k, v in cpm.provider_capture_descriptor(view).items()
                                     if k != "diagnostics"),
        }
        return answers, provenance

    def _release(self, lease):
        """Release in every path. On failure, hand the lease to the broker's
        durable unreleased-lease registry and report it; the caller then
        fails closed."""
        try:
            self._broker.release_view_lease(lease)
            return None
        except Exception as exc:
            message = "view lease release failed: %r" % (exc,)
        try:
            self._broker.register_unreleased_lease(lease, description="CPM authority adapter: " + message)
        except Exception:
            pass
        return (CpmAuthorityUnavailable, u"lease-release-failed", message)

    # -- Part F: health ------------------------------------------------------

    def assess_health(self, literals):
        """Migrated authority health: healthy only if the full bounded chain
        succeeds for the requested vocabulary. Never raises for an
        authority failure; returns ``status`` unavailable instead. The
        advisory unrecognized-control figure never changes ``status``."""
        try:
            descriptor = self.generation_descriptor()
            answers, provenance = self._bounded_read(literals, self._pinned_sha)
        except CpmAuthorityUnavailable as exc:
            return {
                "status": HEALTH_UNAVAILABLE,
                "reason": exc.reason,
                "message": _TEXT(exc),
                "descriptor": None,
                "advisory": None,
            }
        unknown = sorted(k for k, a in answers.items() if a["status"] == cpm.STATUS_ABSENT)
        return {
            "status": HEALTH_HEALTHY,
            "reason": u"canonical-admission-and-view-validated",
            "message": None,
            "descriptor": descriptor,
            "provenance": provenance,
            "advisory": {
                "requested_literal_count": len(answers),
                "master_unknown_literal_count": len(unknown),
                "many_unrecognized": len(unknown) >= ADVISORY_UNRECOGNIZED_THRESHOLD,
            },
        }

    # -- Part H: freshness ---------------------------------------------------

    def verify_current_generation(self, expected_master_sha256, literals):
        """Prove that ``expected_master_sha256`` is still the current
        authority generation, using the canonical broker path (which
        re-observes the Master even on a full cache hit). Returns detached
        provenance only. Raises CpmGenerationMismatch if the generation
        changed; performs no reinterpretation, rebuild or replay."""
        expected = _TEXT(expected_master_sha256).lower()
        cpm.compatibility_identity(expected, self._policy)  # validates the SHA shape
        _, provenance = self._bounded_read(literals, expected)
        return provenance

    # -- bounded stage with an explicitly held lease (Clothing Fit, Step 4) --

    def open_stage(self, expected_master_sha256, literals):
        """Acquire/reuse the cpm_compat_v1 view for ``literals`` under
        ``expected_generation`` and keep its lease until the returned stage
        is released. Validates authorization, generation and complete
        coverage before returning. Used where the Blueprint deliberately
        holds one stage lease through planning, mutation and post-stage
        verification (handoff section 15)."""
        expected = _TEXT(expected_master_sha256).lower()
        cpm.compatibility_identity(expected, self._policy)  # validates the SHA shape
        literal_list = [cpm._to_text(item, "literal") for item in literals]
        folds = cpm.request_folds_for_literals(literal_list)
        specs = cpm.make_request_specs(folds)
        self._operation_count += 1
        failure = None
        view = None
        try:
            views = self._broker.acquire_or_reuse_views(
                self._master_path, specs, shipped_root=self._shipped_root,
                expected_generation=expected,
            )
            view = views.get(cpm.CONSUMER_KIND) if isinstance(views, dict) else None
            views = None
        except Exception as exc:
            failure = _detach(_classify_broker_error(exc))
        if failure is None and view is None:
            failure = (CpmAuthorityUnavailable, u"view-missing", "broker returned no cpm_compat_v1 view")
        if failure is not None:
            view = None
            raise failure[0](failure[1], failure[2])

        lease = None
        try:
            lease = self._broker.lease_view(view)
        except Exception as exc:
            failure = (CpmAuthorityUnavailable, u"lease-refused", "view lease refused: %r" % (exc,))
        if failure is not None:
            view = None
            raise failure[0](failure[1], failure[2])

        try:
            self._materialize(view, folds, [], expected)
        except CpmAuthorityUnavailable as exc:
            failure = _detach(exc)
        except Exception as exc:
            failure = (CpmAuthorityUnavailable, u"projection-invalid", "cpm_compat_v1 validation failed: %s" % (exc,))
        if failure is not None:
            # The validation failure is reported; a release failure is already
            # durably registered with the broker by _release().
            self._release(lease)
            lease = None
            view = None
            raise failure[0](failure[1], failure[2])
        stage = CpmStageAuthority(self._broker, lease, view, folds, expected, self._release)
        lease = None
        view = None
        return stage

    # -- diagnostics ---------------------------------------------------------

    def diagnostics(self):
        return {"operation_count": self._operation_count, "pinned_generation": self._pinned_sha}


class CpmStageAuthority(object):
    """One bounded authority stage: a held lease on one validated
    cpm_compat_v1 view for one generation and one covered vocabulary.
    Provider-shaped for ``query_many`` only. Answers only covered literals
    (Uncovered fails closed; it never triggers another acquisition) and
    only while the lease is held and its authorization is valid. After
    ``release()`` it holds no lease or view."""

    def __init__(self, broker, lease, view, folds, generation, release_fn):
        self._broker = broker
        self._lease = lease
        self._view = view
        self._folds = frozenset(folds)
        self._release_fn = release_fn
        self.generation = generation

    def is_released(self):
        return self._lease is None

    def covered_folds(self):
        return self._folds

    def query_many(self, literals):
        if self._lease is None or self._view is None:
            raise CpmAuthorityUnavailable(u"stage-released", "the authority stage was already released")
        literal_list = [cpm._to_text(item, "literal") for item in literals]
        folds = cpm.request_folds_for_literals(literal_list)
        if not folds <= self._folds:
            raise CpmAuthorityUnavailable(
                u"stage-uncovered", "%d requested literals are outside this stage's covered vocabulary"
                % len(folds - self._folds))
        token = getattr(self._view, "authorization", None)
        if token is None or not token.is_valid():
            raise CpmAuthorityUnavailable(u"authorization-invalid", "stage authorization is no longer valid")
        return cpm.interpret_exact_answers(literal_list, self._view.payload)

    def release(self):
        """Release the lease and clear every reference. Returns None on
        success, or the (class, reason, message) failure triple after the
        lease was handed to the broker's durable unreleased-lease registry."""
        lease = self._lease
        self._lease = None
        self._view = None
        if lease is None:
            return None
        result = self._release_fn(lease)
        lease = None
        self._release_fn = None
        self._broker = None
        return result
