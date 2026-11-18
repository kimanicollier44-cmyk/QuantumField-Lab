"""Tests for QuantumField-Lab: dispersion, vacuum, packet, quench, gates."""
import math

import pytest

import main as m


# ---- dispersion: lattice vs continuum
def test_omega_zero_mode_is_mass():
    assert m.omega_lattice(0.0, 1.0, 0.5) == 0.5
    assert m.omega_continuum(0.0, 0.5) == 0.5


def test_lattice_below_continuum():
    for k in (0.1, 0.6, 1.0, 2.0, math.pi):
        assert m.omega_lattice(k, 1.0, 0.5) <= m.omega_continuum(k, 0.5)


def test_zone_edge_frequency_and_deviation():
    assert m.omega_lattice(math.pi, 1.0, 0.5) == pytest.approx(
        math.sqrt(4.25), abs=1e-12)
    assert m.dispersion_deviation(math.pi, 1.0, 0.5) == pytest.approx(
        0.351944, abs=1e-6)
    assert m.dispersion_deviation(0.6, 1.0, 0.5) == pytest.approx(
        0.008786, abs=1e-6)


def test_deviation_grows_with_k():
    devs = [m.dispersion_deviation(k, 1.0, 0.5)
            for k in (0.6, 1.0, math.pi / 2, math.pi)]
    assert devs == sorted(devs)


def test_dispersion_report_shape():
    rep = m.dispersion_report()
    assert len(rep["rows"]) == 8
    assert rep["rows"][0]["rel_deviation"] == 0.0
    assert rep["rows"][-1]["k"] == pytest.approx(math.pi, abs=1e-6)
    assert rep == m.dispersion_report()


def test_group_velocities():
    assert m.group_velocity_lattice(0.6, 1.0, 0.5) == pytest.approx(
        0.729358, abs=1e-6)
    assert m.group_velocity_continuum(0.6, 0.5) == pytest.approx(
        0.768221, abs=1e-6)
    assert m.group_velocity_lattice(0.0, 1.0, 0.5) == 0.0
    assert m.group_velocity_error(1.2, 2.0, 0.5) > 0.6


# ---- vacuum energy: divergent sum, convergent difference
def test_vacuum_energy_values():
    assert m.vacuum_energy(64, 1.0, 0.5) == pytest.approx(
        44.890737, abs=1e-6)
    assert m.vacuum_energy(64, 1.0, 1.5) == pytest.approx(
        65.003969, abs=1e-6)
    assert m.vacuum_energy(64, 1.0, 1.5) > m.vacuum_energy(64, 1.0, 0.5)


def test_vacuum_volume_growth_linear():
    assert m.vacuum_energy(128, 1.0, 0.5) == pytest.approx(
        2.0 * m.vacuum_energy(64, 1.0, 0.5), rel=1e-9)


def test_vacuum_report_growth_and_difference():
    rep = m.vacuum_report()
    rows = rep["fixed_volume_refinement"]
    assert all(rows[i + 1]["e0"] > rows[i]["e0"] for i in range(3))
    assert 45.0 < rep["refinement_growth_factor"] < 55.0
    assert rep["mass_difference_fixed_lattice"] == pytest.approx(
        -20.113232, abs=1e-4)


def test_casimir_converges():
    diffs = [m.casimir_difference(n, 8.0, 0.5)
             for n in (32, 64, 128, 256)]
    changes = [abs(diffs[i + 1] - diffs[i]) for i in range(3)]
    assert changes[2] < changes[1] < changes[0]
    assert diffs[-1] == pytest.approx(-0.003974, abs=1e-6)


def test_casimir_massless_matches_continuum():
    assert m.casimir_difference(128, 8.0, 0.0) == pytest.approx(
        -math.pi / 32.0, abs=5e-6)


# ---- wavepacket: measured speed vs three predictions
def test_packet_measurement():
    rep = m.packet_report()
    assert rep["intensity_conserved"] is True
    assert rep["intensity_total"] == pytest.approx(128.0, abs=1e-6)
    assert rep["start_position"] == pytest.approx(64.0, abs=1e-6)
    assert rep["v_measured"] == pytest.approx(0.720064, abs=1e-6)
    assert rep["err_vs_weighted"] < 0.002
    assert rep["v_measured"] < rep["v_central_lattice"] \
        < rep["v_continuum"]
    assert 0.04 < rep["err_vs_continuum"] < 0.08


# ---- quench: Bogoliubov arithmetic, sudden vs smooth
def test_beta2_zero_mode_exact():
    assert m.beta2_sudden_mode(0.0, 1.0, 0.5, 1.5) == pytest.approx(
        1.0 / 3.0, abs=1e-12)


def test_bogoliubov_unitarity():
    for k in m.lattice_momenta(64, 1.0):
        assert m.alpha2_sudden_mode(k, 1.0, 0.5, 1.5) \
            - m.beta2_sudden_mode(k, 1.0, 0.5, 1.5) == pytest.approx(
                1.0, abs=1e-12)


def test_no_quench_no_particles():
    assert m.beta2_sudden_total(64, 1.0, 0.5, 0.5) == 0.0


def test_quench_totals_and_suppression():
    rep = m.quench_report()
    assert rep["totals"]["sudden_jump"] == pytest.approx(
        4.722298, abs=1e-6)
    assert rep["totals"]["smooth_tau_5"] < rep["totals"]["smooth_tau_1"] \
        < rep["totals"]["sudden_jump"]
    assert 0.30 < rep["totals"]["smooth_tau_5"] < 0.33
    assert rep["beta2_at_k0"] == pytest.approx(1.0 / 3.0, abs=1e-6)


def test_numeric_near_sudden_limit():
    numeric = m.beta2_smooth_total(tau=0.05, dt=0.002, tail=2.0)
    assert abs(numeric - m.beta2_sudden_total()) \
        / m.beta2_sudden_total() < 0.02


# ---- correlations: massive dies fast, massless lingers
def test_correlation_values():
    rep = m.correlation_report()
    assert rep["massive"][0] == pytest.approx(0.436998, abs=1e-6)
    assert rep["massive"][8] == pytest.approx(0.001816, abs=1e-6)
    assert rep["massless_zero_mode_omitted"][0] == pytest.approx(
        0.792218, abs=1e-6)


def test_correlation_decay_contrast():
    rep = m.correlation_report()
    mv = rep["massive"]
    assert mv[0] > mv[1] > mv[2] > mv[4] > mv[8] > mv[16] > 0.0
    assert rep["ratio_at_8_massive"] < 0.01 < rep["ratio_at_8_massless"]
    assert rep["ratio_at_8_massless"] > 10.0 * rep["ratio_at_8_massive"]


def test_correlation_symmetric():
    assert m.correlation_value(5) == pytest.approx(
        m.correlation_value(128 - 5), abs=1e-12)


# ---- classifier
def test_classifier_report():
    rep = m.classifier_report()
    assert rep["sudden_quench_demo_lattice"] == "quench-violent"
    assert rep["coarse_lattice_gentle_quench"] == "lattice-artefact"
    assert rep["smooth_ramp_demo_lattice"] == "quench-adiabatic"
    assert rep["fine_lattice_no_quench"] == "continuum-like"


def test_classifier_matches_policy():
    for features in m.scenario_features().values():
        assert m.classify_regime(*features) == m.regime_policy(*features)


def test_policy_thresholds():
    assert m.regime_policy(0.0, 1.0, 0.0) == "quench-violent"
    assert m.regime_policy(0.1, 0.0, 0.0) == "lattice-artefact"
    assert m.regime_policy(0.0, 0.1, 0.0) == "quench-adiabatic"
    assert m.regime_policy(0.0, 0.0, 0.0) == "continuum-like"


# ---- gates + seats
def test_hold_gates_14():
    assert len(m.HOLD_GATES) == 14
    assert all(v.startswith("HOLD") for v in m.HOLD_GATES.values())


def test_gate_specifics():
    assert m.gate("cosmology_claim") == "HOLD"
    assert m.gate("particle_physics_prediction") == "HOLD"
    assert m.gate("real_particle_creation_claim") == "HOLD"
    assert m.gate("vacuum_energy_cosmology_claim") == "HOLD"
    assert m.gate("faster_than_light_claim") == "HOLD"
    assert m.gate("run_simulation") == "PROCEED"


def test_seats_cannot_override():
    b = m.brains_report()
    assert b["decider"]["seat"] == "Gemini Argon 4 Extended Thinking"
    assert b["decider"]["model_id"] == "gemini-argon-4"
    assert b["decider"]["can_override_hold"] is False
    assert b["advisor"]["can_override_hold"] is False
    assert b["flow"]["rendered"] is False and b["flow"]["live"] == 0


def test_checks_all_pass():
    checks = m.run_checks()
    assert all(ok for _, ok in checks), [n for n, ok in checks if not ok]


def test_hold_demo_exit_code():
    assert m.main(["hold-demo", "cosmology_claim"]) == 2
    assert m.main(["hold-demo", "run_simulation"]) == 0
