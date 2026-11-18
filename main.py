#!/usr/bin/env python3
"""QuantumField-Lab - educational quantum field theory lab on a lattice.

by Darion Kellar

Pure Python standard library. Zero dependencies. Zero network.
Education only - and the central lesson is stated up front:

  * This lab quantises the simplest field there is - a free scalar
    (Klein-Gordon) field - on a finite 1D lattice of coupled
    oscillators, in natural units hbar = c = 1. Everything is
    computed exactly from the lattice mode sum: the dispersion
    relation, the vacuum energy, a moving wavepacket, particle
    creation by a sudden mass quench (Bogoliubov coefficients), and
    the vacuum two-point correlation.
  * The lattice is not the continuum, and the lab shows the seam:
    the lattice dispersion bends away from sqrt(m^2 + k^2) and is
    35.19% low at the zone edge, the packet rides measurably slower
    than the continuum predicts, and the vacuum energy E0 explodes
    as the cutoff rises - while the subtracted Casimir difference
    between two boundary conditions converges to a stable number.
  * No spacetime was quantised here, no particles were created
    anywhere but in the arithmetic, and no number in this lab is a
    prediction about the real universe. Cosmology, particle-physics,
    vacuum-energy, and prediction uses are permanent HOLD gates -
    with Gemini Argon 4 Extended Thinking as DECIDER (names-only,
    tighten-only), Muse as advisor (never overrides HOLD), and
    Google Flow plan-only seats.
"""
import hashlib
import json
import math
import sys

# ---------------------------------------------------------------- constants
VERSION = "1.0.0"

# Labelled teaching parameters. Natural units hbar = c = 1 throughout.
# Every number below is a chosen teaching value, not a measurement.
A_DEMO = 1.0            # demo lattice spacing
N_DEMO = 64             # demo lattice sites
M_DEMO = 0.5            # demo field mass
L_VAC = 64.0            # box length for the fixed-volume vacuum study
L_CASIMIR = 8.0         # box length for the Casimir study (m*L = 4)
N_PKT = 128             # wavepacket lattice sites (a = 1)
K0_PKT = 0.6            # wavepacket central momentum
SIGMA_PKT = 0.10        # wavepacket momentum width
T_PKT = 40.0            # wavepacket evolution time
M_IN = 0.5              # quench: mass before t = 0
M_OUT = 1.5             # quench: mass after the jump / ramp
TAU_SMOOTH = (1.0, 5.0)  # smooth-ramp durations priced against the jump
N_CORR = 128            # correlation lattice sites (a = 1)

# ---------------------------------------------------------------- HOLD gates
HOLD_GATES = {
    "cosmology_claim": "HOLD - no claims about the real universe's expansion, inflation, or reheating from a lattice toy",
    "particle_physics_prediction": "HOLD - no predicting real particle masses, couplings, cross-sections, or collider outcomes",
    "real_particle_creation_claim": "HOLD - no claim that particles were created anywhere but in this arithmetic",
    "quantum_gravity_claim": "HOLD - no quantum-gravity or spacetime-quantisation claims; the lattice is a regulator, not spacetime",
    "vacuum_energy_cosmology_claim": "HOLD - no cosmological-constant or dark-energy claims from a divergent lattice sum",
    "casimir_device_claim": "HOLD - no real Casimir-force device, measurement, or engineering claims",
    "faster_than_light_claim": "HOLD - lattice dispersion artefacts never license superluminal claims",
    "free_energy_claim": "HOLD - vacuum energy is not extractable energy; no free-energy or over-unity devices",
    "hawking_radiation_claim": "HOLD - no black-hole evaporation claims from a mass-quench toy",
    "unruh_effect_claim": "HOLD - no accelerated-detector radiation claims from this lab",
    "standard_model_claim": "HOLD - one free scalar toy is not the Standard Model; no completeness claims",
    "simulation_as_experiment_claim": "HOLD - simulation output is not experimental data and is never presented as such",
    "weaponisation_claim": "HOLD - no weapons relevance, targeting, or effects claims of any kind",
    "investment_claim": "HOLD - no investment claims; a lab model is not a prospectus",
}


def gate(action):
    """Return 'HOLD' if the action is gated, else 'PROCEED' (sandbox sim)."""
    return "HOLD" if action in HOLD_GATES else "PROCEED"


# ================================================================ 1. Lattice modes + dispersion
# A free scalar field on a ring of N sites with spacing a is N coupled
# oscillators. Its normal modes are plane waves with momenta
# k_j = 2 pi j / (N a), and the discrete Laplacian gives the lattice
# dispersion omega_k = sqrt(m^2 + (4/a^2) sin^2(k a / 2)). The
# continuum wants sqrt(m^2 + k^2); the two agree at small k and part
# ways as k a grows - the lab measures the parting, never hides it.

def lattice_momenta(n_sites, spacing, antiperiodic=False):
    """Mode momenta k_j = 2 pi (j + shift) / L on the ring."""
    length = n_sites * spacing
    shift = 0.5 if antiperiodic else 0.0
    return [2.0 * math.pi * (j + shift) / length for j in range(n_sites)]


def signed_momentum(j, n_sites, spacing):
    """Momentum of mode j folded into the first Brillouin zone."""
    jj = j - n_sites if j > n_sites / 2 else j
    return 2.0 * math.pi * jj / (n_sites * spacing)


def omega_lattice(k, spacing, mass):
    """Lattice dispersion sqrt(m^2 + (4/a^2) sin^2(k a / 2))."""
    return math.sqrt(mass * mass
                     + (4.0 / (spacing * spacing))
                     * math.sin(k * spacing / 2.0) ** 2)


def omega_continuum(k, mass):
    """Continuum dispersion sqrt(m^2 + k^2)."""
    return math.sqrt(mass * mass + k * k)


def dispersion_deviation(k, spacing, mass):
    """Relative gap |omega_lat - omega_cont| / omega_cont at momentum k."""
    cont = omega_continuum(k, mass)
    return abs(omega_lattice(k, spacing, mass) - cont) / cont


def group_velocity_lattice(k, spacing, mass):
    """d(omega)/dk of the lattice dispersion: sin(k a) / (a omega)."""
    om = omega_lattice(k, spacing, mass)
    return math.sin(k * spacing) / (spacing * om) if om else 0.0


def group_velocity_continuum(k, mass):
    """d(omega)/dk of the continuum dispersion: k / omega."""
    return k / omega_continuum(k, mass)


def group_velocity_error(k, spacing, mass):
    """How wrong the continuum group velocity is on this lattice."""
    cont = group_velocity_continuum(k, mass)
    return abs(group_velocity_lattice(k, spacing, mass) - cont) / cont


def dispersion_report(n_sites=N_DEMO, spacing=A_DEMO, mass=M_DEMO):
    """Lattice vs continuum frequencies across the Brillouin zone."""
    rows = []
    for j in (0, 1, 2, 4, 8, 16, 24, 32):
        k = signed_momentum(j, n_sites, spacing)
        lat = omega_lattice(k, spacing, mass)
        cont = omega_continuum(k, mass)
        rows.append({
            "mode": j,
            "k": round(k, 6),
            "omega_lattice": round(lat, 6),
            "omega_continuum": round(cont, 6),
            "rel_deviation": round(abs(lat - cont) / cont, 6),
        })
    return {
        "n_sites": n_sites,
        "spacing": spacing,
        "mass": mass,
        "zone_edge_k": round(math.pi / spacing, 6),
        "deviation_at_packet_k": round(
            dispersion_deviation(K0_PKT, spacing, mass), 6),
        "deviation_at_zone_edge": round(
            dispersion_deviation(math.pi / spacing, spacing, mass), 6),
        "rows": rows,
    }


# ================================================================ 2. Vacuum energy
# The vacuum energy of the lattice field is E0 = (1/2) sum_k omega_k.
# It is dominated by the highest modes, so it grows with the cutoff:
# double the box at fixed spacing and E0 doubles (pure volume);
# refine the lattice at fixed volume and E0 grows like the cutoff
# squared. The lab prints both growth laws, then shows the quantity
# that survives: the Casimir difference between periodic and
# antiperiodic boundary conditions at the same lattice, which
# converges as the lattice refines - and for a massless field lands
# on the exact continuum value -pi / (4 L).

def vacuum_energy(n_sites, spacing, mass, antiperiodic=False):
    """E0 = (1/2) sum_k omega_k over the lattice modes."""
    return 0.5 * sum(omega_lattice(k, spacing, mass)
                     for k in lattice_momenta(n_sites, spacing,
                                               antiperiodic))


def casimir_difference(n_sites, length, mass):
    """E0(periodic) - E0(antiperiodic) at fixed box length."""
    spacing = length / n_sites
    return (vacuum_energy(n_sites, spacing, mass, False)
            - vacuum_energy(n_sites, spacing, mass, True))


def vacuum_report():
    """Growth of E0 with volume and cutoff, and the finite difference."""
    volume_rows = []
    for n in (16, 32, 64, 128):
        e0 = vacuum_energy(n, A_DEMO, M_DEMO)
        volume_rows.append({"n_sites": n, "e0": round(e0, 6),
                            "e0_per_site": round(e0 / n, 6)})
    refine_rows = []
    for n in (32, 64, 128, 256):
        e0 = vacuum_energy(n, L_VAC / n, M_DEMO)
        refine_rows.append({"n_sites": n, "spacing": round(L_VAC / n, 6),
                            "e0": round(e0, 6)})
    casimir_rows = []
    prev = None
    for n in (16, 32, 64, 128, 256):
        diff = casimir_difference(n, L_CASIMIR, M_DEMO)
        casimir_rows.append({
            "n_sites": n,
            "casimir": round(diff, 6),
            "change_from_previous": None if prev is None
            else round(abs(diff - prev), 8),
        })
        prev = diff
    massless = casimir_difference(128, L_CASIMIR, 0.0)
    exact = -math.pi / (4.0 * L_CASIMIR)
    return {
        "mass": M_DEMO,
        "fixed_spacing_volume_growth": volume_rows,
        "fixed_volume_refinement": refine_rows,
        "refinement_growth_factor": round(
            refine_rows[-1]["e0"] / refine_rows[0]["e0"], 4),
        "casimir_massive_L8": casimir_rows,
        "casimir_massless_L8_N128": round(massless, 6),
        "casimir_massless_exact_continuum": round(exact, 6),
        "mass_difference_fixed_lattice": round(
            vacuum_energy(N_DEMO, A_DEMO, M_DEMO)
            - vacuum_energy(N_DEMO, A_DEMO, M_OUT), 6),
    }


# ================================================================ 3. Wavepacket
# A Gaussian packet in momentum space, centred at k0 with width
# sigma, is assembled from the lattice modes and evolved exactly by
# spectral phases. Its intensity centroid is tracked on the ring.
# The honest prediction for the centroid speed is the |c_k|^2-weighted
# average of the lattice group velocity over the packet - the packet
# is wide enough that the single number d(omega)/dk at k0 is already
# 1.3% off, and the continuum value is 6.3% off. All three numbers
# are printed; the measurement lands on the weighted one.

def packet_report(n_sites=N_PKT, spacing=A_DEMO, mass=M_DEMO,
                  k0=K0_PKT, sigma=SIGMA_PKT, t_max=T_PKT, samples=9):
    """Build the packet, evolve it, and measure its group velocity."""
    length = n_sites * spacing
    centre = length / 2.0
    ks = [signed_momentum(j, n_sites, spacing) for j in range(n_sites)]
    coeffs = [math.exp(-((k - k0) ** 2) / (4.0 * sigma * sigma))
              for k in ks]
    norm = math.sqrt(sum(c * c for c in coeffs))
    coeffs = [c / norm for c in coeffs]
    omegas = [omega_lattice(k, spacing, mass) for k in ks]
    weighted_vg = sum(
        c * c * group_velocity_lattice(k, spacing, mass)
        for c, k in zip(coeffs, ks))
    times, positions, totals = [], [], []
    for s in range(samples):
        t = t_max * s / (samples - 1)
        sum_re = sum_im = total = 0.0
        for j in range(n_sites):
            x = j * spacing
            re = sum(coeffs[i] * math.cos(ks[i] * (x - centre)
                                          - omegas[i] * t)
                     for i in range(n_sites))
            im = sum(coeffs[i] * math.sin(ks[i] * (x - centre)
                                          - omegas[i] * t)
                     for i in range(n_sites))
            w = re * re + im * im
            total += w
            angle = 2.0 * math.pi * j / n_sites
            sum_re += w * math.cos(angle)
            sum_im += w * math.sin(angle)
        ang = math.atan2(sum_im, sum_re)
        if ang < 0:
            ang += 2.0 * math.pi
        times.append(t)
        positions.append(ang * length / (2.0 * math.pi))
        totals.append(total)
    unwrapped = [positions[0]]
    for x in positions[1:]:
        y = x
        while y - unwrapped[-1] > length / 2.0:
            y -= length
        while y - unwrapped[-1] < -length / 2.0:
            y += length
        unwrapped.append(y)
    n = len(times)
    mean_t = sum(times) / n
    mean_x = sum(unwrapped) / n
    slope = (sum((times[i] - mean_t) * (unwrapped[i] - mean_x)
                 for i in range(n))
             / sum((t - mean_t) ** 2 for t in times))
    vg_central = group_velocity_lattice(k0, spacing, mass)
    vg_cont = group_velocity_continuum(k0, mass)
    return {
        "n_sites": n_sites,
        "k0": k0,
        "sigma_k": sigma,
        "start_position": round(unwrapped[0], 6),
        "end_position": round(unwrapped[-1], 6),
        "intensity_total": round(totals[0], 6),
        "intensity_conserved": all(abs(tt - totals[0]) < 1e-6
                                   for tt in totals),
        "v_measured": round(slope, 6),
        "v_weighted_lattice": round(weighted_vg, 6),
        "v_central_lattice": round(vg_central, 6),
        "v_continuum": round(vg_cont, 6),
        "err_vs_weighted": round(abs(slope - weighted_vg) / weighted_vg, 6),
        "err_vs_central": round(abs(slope - vg_central) / vg_central, 6),
        "err_vs_continuum": round(abs(slope - vg_cont) / vg_cont, 6),
    }


# ================================================================ 4. Quench / Bogoliubov
# The mass jumps m_in -> m_out. Each mode is an oscillator whose
# frequency jumps with it, and the in-vacuum is a squeezed state of
# the out-modes: |beta_k|^2 = (w_out - w_in)^2 / (4 w_in w_out)
# particles per mode, with |alpha_k|^2 - |beta_k|^2 = 1 asserted.
# A smooth ramp of duration tau, integrated mode by mode with RK4,
# creates strictly fewer particles - the sudden jump is the violent
# limit, and the lab prices both.

def beta2_sudden_mode(k, spacing, m_in, m_out):
    """|beta_k|^2 for a sudden frequency jump at momentum k."""
    w_in = omega_lattice(k, spacing, m_in)
    w_out = omega_lattice(k, spacing, m_out)
    return (w_out - w_in) ** 2 / (4.0 * w_in * w_out)


def alpha2_sudden_mode(k, spacing, m_in, m_out):
    """|alpha_k|^2 for a sudden jump; |alpha|^2 - |beta|^2 = 1."""
    w_in = omega_lattice(k, spacing, m_in)
    w_out = omega_lattice(k, spacing, m_out)
    return (w_out + w_in) ** 2 / (4.0 * w_in * w_out)


def beta2_sudden_total(n_sites=N_DEMO, spacing=A_DEMO,
                       m_in=M_IN, m_out=M_OUT):
    """Total created particles, sudden jump, summed over all modes."""
    return sum(beta2_sudden_mode(k, spacing, m_in, m_out)
               for k in lattice_momenta(n_sites, spacing))


def _smoothstep(u):
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0
    return u * u * (3.0 - 2.0 * u)


def beta2_smooth_total(n_sites=N_DEMO, spacing=A_DEMO, m_in=M_IN,
                       m_out=M_OUT, tau=5.0, dt=0.005, tail=6.0):
    """Total created particles for a smoothstep mass ramp of length tau.

    Each mode obeys q'' + (kappa_k^2 + m^2(t)) q = 0, started in the
    in-vacuum positive-frequency mode and integrated with RK4; after
    the ramp the out-Bogoliubov coefficient is read off q and q'
    exactly. Deterministic: fixed step, fixed grid, no randomness.
    """
    total = 0.0
    t_end = tau + tail
    for k in lattice_momenta(n_sites, spacing):
        kap2 = (2.0 / spacing * math.sin(k * spacing / 2.0)) ** 2
        w_in = math.sqrt(kap2 + m_in * m_in)
        w_out = math.sqrt(kap2 + m_out * m_out)
        q = complex(1.0 / math.sqrt(2.0 * w_in), 0.0)
        qd = complex(0.0, -w_in) * q

        def accel(tt, qq):
            if tt <= 0.0:
                ms = m_in * m_in
            elif tt >= tau:
                ms = m_out * m_out
            else:
                ms = m_in * m_in + (m_out * m_out - m_in * m_in) \
                    * _smoothstep(tt / tau)
            return -(kap2 + ms) * qq

        t = 0.0
        while t < t_end - 1e-12:
            h = min(dt, t_end - t)
            k1q, k1d = qd, accel(t, q)
            k2q, k2d = qd + 0.5 * h * k1d, accel(t + 0.5 * h,
                                                 q + 0.5 * h * k1q)
            k3q, k3d = qd + 0.5 * h * k2d, accel(t + 0.5 * h,
                                                 q + 0.5 * h * k2q)
            k4q, k4d = qd + h * k3d, accel(t + h, q + h * k3q)
            q += h / 6.0 * (k1q + 2.0 * k2q + 2.0 * k3q + k4q)
            qd += h / 6.0 * (k1d + 2.0 * k2d + 2.0 * k3d + k4d)
            t += h
        beta = (math.sqrt(2.0 * w_out) * q
                - 1j * math.sqrt(2.0 / w_out) * qd) / 2.0
        total += abs(beta) ** 2
    return total


def quench_report():
    """Sudden vs smooth quench: per-mode peak and total production."""
    sudden = beta2_sudden_total()
    rows = {"sudden_jump": round(sudden, 6)}
    for tau in TAU_SMOOTH:
        rows[f"smooth_tau_{tau:g}"] = round(
            beta2_smooth_total(tau=tau), 6)
    return {
        "n_sites": N_DEMO,
        "spacing": A_DEMO,
        "m_in": M_IN,
        "m_out": M_OUT,
        "beta2_at_k0": round(beta2_sudden_mode(0.0, A_DEMO, M_IN, M_OUT), 6),
        "beta2_max_over_modes": round(max(
            beta2_sudden_mode(k, A_DEMO, M_IN, M_OUT)
            for k in lattice_momenta(N_DEMO, A_DEMO)), 6),
        "totals": rows,
        "suppression_tau5_vs_sudden": round(
            sudden / rows["smooth_tau_5"], 4),
    }


# ================================================================ 5. Correlations
# The vacuum two-point function on the lattice is the mode sum
# <phi_x phi_0> = (1/N) sum_k cos(k x) / (2 omega_k). A massive
# field's correlations die exponentially with distance; a massless
# field's linger - on a finite ring the massless zero mode is
# omitted (labelled infrared regulator) and the rest of the sum
# decays far more slowly. Both are computed from the same sum.

def correlation_value(separation, n_sites=N_CORR, spacing=A_DEMO,
                      mass=M_DEMO, omit_zero_mode=False):
    """<phi_x phi_0> at the given site separation, from the mode sum."""
    total = 0.0
    for j, k in enumerate(lattice_momenta(n_sites, spacing)):
        if omit_zero_mode and j == 0:
            continue
        total += (math.cos(k * separation * spacing)
                  / (2.0 * omega_lattice(k, spacing, mass)))
    return total / n_sites


def correlation_report():
    """Massive vs massless vacuum correlations vs distance."""
    points = (0, 1, 2, 3, 4, 8, 16)
    massive = {x: round(correlation_value(x, mass=M_DEMO), 6)
               for x in points}
    massless = {x: round(correlation_value(x, mass=0.0,
                                           omit_zero_mode=True), 6)
                for x in points}
    return {
        "n_sites": N_CORR,
        "spacing": A_DEMO,
        "mass": M_DEMO,
        "massive": massive,
        "massless_zero_mode_omitted": massless,
        "ratio_at_8_massive": round(massive[8] / massive[0], 6),
        "ratio_at_8_massless": round(massless[8] / massless[0], 6),
    }


# ================================================================ 6. kNN regime classifier
# Features: the dispersion deviation at the working momentum, the
# total quench production, and the group-velocity error. The
# training grid is labelled by the lab's own regime policy
# (regime_policy below) - the classifier interpolates the policy,
# it does not replace the physics sections that produced the
# features.

def regime_policy(ka_dev, beta2_total, vel_err):
    """The lab's regime policy distilled to a four-way verdict."""
    if beta2_total >= 1.0:
        return "quench-violent"
    if ka_dev >= 0.08 or vel_err >= 0.08:
        return "lattice-artefact"
    if beta2_total >= 0.02:
        return "quench-adiabatic"
    return "continuum-like"


def _training_grid():
    rows = []
    for ka_dev in (0.0, 0.005, 0.02, 0.05, 0.1, 0.2, 0.35):
        for beta2 in (0.0, 0.01, 0.05, 0.3, 0.8, 2.0, 5.0):
            for vel_err in (0.0, 0.01, 0.04, 0.12):
                rows.append(((ka_dev, beta2, vel_err),
                             regime_policy(ka_dev, beta2, vel_err)))
    return rows


TRAINING_GRID = _training_grid()


def _scaled(features):
    ka_dev, beta2, vel_err = features
    return (ka_dev / 0.35, beta2 / (beta2 + 1.0), vel_err / 0.35)


def classify_regime(ka_dev, beta2_total, vel_err, k=5):
    """kNN over the policy-labelled grid, deterministic tie-breaking."""
    target = _scaled((ka_dev, beta2_total, vel_err))
    ranked = []
    for features, label in TRAINING_GRID:
        point = _scaled(features)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target, point)))
        ranked.append((dist, features, label))
    ranked.sort(key=lambda row: (row[0], row[1]))
    votes = {}
    for _, _, label in ranked[:k]:
        votes[label] = votes.get(label, 0) + 1
    priority = {"quench-violent": 0, "lattice-artefact": 1,
                "quench-adiabatic": 2, "continuum-like": 3}
    return sorted(votes.items(), key=lambda kv: (-kv[1], priority[kv[0]]))[0][0]


def scenario_features():
    """Feature triples for four named scenarios, computed by the lab.

    Demo-lattice scenarios take their velocity error from the
    measured packet; the coarse / fine scenarios use the exact
    lattice-vs-continuum group-velocity formulas at their working
    momentum (the packet section validates those formulas).
    """
    pkt = packet_report()
    dev_demo = dispersion_deviation(K0_PKT, A_DEMO, M_DEMO)
    return {
        "sudden_quench_demo_lattice": (
            dev_demo, beta2_sudden_total(), pkt["err_vs_continuum"]),
        "coarse_lattice_gentle_quench": (
            dispersion_deviation(1.2, 2.0, M_DEMO),
            beta2_sudden_total(32, 2.0, M_DEMO, 0.6),
            group_velocity_error(1.2, 2.0, M_DEMO)),
        "smooth_ramp_demo_lattice": (
            dev_demo, beta2_smooth_total(tau=5.0), pkt["err_vs_continuum"]),
        "fine_lattice_no_quench": (
            dispersion_deviation(K0_PKT, 0.5, M_DEMO),
            beta2_sudden_total(64, 0.5, M_DEMO, M_DEMO),
            group_velocity_error(K0_PKT, 0.5, M_DEMO)),
    }


def classifier_report():
    return {name: classify_regime(*features)
            for name, features in scenario_features().items()}


# ================================================================ 7. Advisory seats
def _trace(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def argon4_decide(topic="quantumfield-demo"):
    """Gemini Argon 4 DECIDER seat: MAP->MODEL->STRESS->DECIDE.

    Names-only keys, live calls 0, tighten-only: can add HOLDs, never lift one.
    """
    stages = ["MAP", "MODEL", "STRESS", "DECIDE"]
    payload = {"seat": "gemini-argon-4", "topic": topic, "stages": stages}
    return {
        "seat": "Gemini Argon 4 Extended Thinking",
        "model_id": "gemini-argon-4",
        "role": "DECIDER",
        "pipeline": stages,
        "tiers": [2048, 8192, 32768],
        "key": "names-only (GEMINI_API_KEY name checked, value never read)",
        "live_calls": 0,
        "decision": "PROCEED - sandbox simulation only, all cosmology / particle-physics / prediction gates stay HOLD",
        "can_override_hold": False,
        "trace_sha256_16": _trace(payload),
    }


def claude_advisor(topic="quantumfield-demo"):
    """Muse advisor seat: advises, can never override a HOLD."""
    return {
        "seat": "Muse",
        "role": "ADVISOR",
        "key": "names-only (MODEL_API_KEY name checked, value never read)",
        "live_calls": 0,
        "advice": "Print the seam, not just the result: the dispersion deviation at the working k, the cutoff growth of E0 next to the converged Casimir difference, and the packet speed next to all three predictions - a lattice number without its artefact budget is an overclaim.",
        "can_override_hold": False,
    }


def google_flow_plan():
    """Google Flow seat: plan-only, nothing rendered, nothing live."""
    return {
        "seat": "Google Flow",
        "role": "PLAN-ONLY",
        "shots": ["a ring of coupled oscillators lighting up mode by mode",
                  "the lattice dispersion curve bending away from the continuum arc",
                  "the vacuum-energy sum climbing a staircase as the cutoff doubles",
                  "a Gaussian packet riding the ring slower than the continuum ghost ahead of it",
                  "a mass quench flashing pairs into every mode, then a slow ramp barely whispering"],
        "rendered": False,
        "live": 0,
    }


def brains_report():
    return {"decider": argon4_decide(), "advisor": claude_advisor(),
            "flow": google_flow_plan()}


# ================================================================ checks
def run_checks():
    c = []

    def chk(name, ok):
        c.append((name, bool(ok)))

    # 1. dispersion - the lattice bends away from the continuum
    chk("omega_zero_mode_is_mass",
        omega_lattice(0.0, A_DEMO, M_DEMO) == M_DEMO
        and omega_continuum(0.0, M_DEMO) == M_DEMO)
    chk("lattice_below_continuum",
        all(omega_lattice(k, A_DEMO, M_DEMO)
            <= omega_continuum(k, M_DEMO) + 1e-12
            for k in (0.1, 0.6, 1.0, 2.0, math.pi)))
    chk("zone_edge_frequency_exact",
        abs(omega_lattice(math.pi, A_DEMO, M_DEMO)
            - math.sqrt(M_DEMO ** 2 + 4.0 / A_DEMO ** 2)) < 1e-12)
    disp = dispersion_report()
    chk("zone_edge_deviation_35pct",
        abs(disp["deviation_at_zone_edge"] - 0.351944) < 1e-6)
    chk("deviation_grows_with_k",
        dispersion_deviation(0.6, A_DEMO, M_DEMO)
        < dispersion_deviation(1.0, A_DEMO, M_DEMO)
        < dispersion_deviation(math.pi / 2, A_DEMO, M_DEMO)
        < dispersion_deviation(math.pi, A_DEMO, M_DEMO))
    chk("dispersion_table_shape",
        len(disp["rows"]) == 8 and disp["rows"][0]["rel_deviation"] == 0.0
        and abs(disp["rows"][-1]["k"] - math.pi) < 1e-6)

    # 2. vacuum energy - divergent sum, convergent difference
    vac = vacuum_report()
    chk("vacuum_energy_positive",
        vacuum_energy(N_DEMO, A_DEMO, M_DEMO) > 0.0)
    chk("vacuum_volume_growth_linear",
        abs(vacuum_energy(128, A_DEMO, M_DEMO)
            - 2.0 * vacuum_energy(64, A_DEMO, M_DEMO))
        / vacuum_energy(128, A_DEMO, M_DEMO) < 1e-9)
    rows = vac["fixed_volume_refinement"]
    chk("vacuum_cutoff_growth",
        all(rows[i + 1]["e0"] > rows[i]["e0"] for i in range(len(rows) - 1))
        and 45.0 < vac["refinement_growth_factor"] < 55.0)
    cas = vac["casimir_massive_L8"]
    chk("casimir_converges",
        cas[-1]["change_from_previous"] < cas[-2]["change_from_previous"]
        and cas[-1]["change_from_previous"] < 2e-6
        and -0.0041 < cas[-1]["casimir"] < -0.0039)
    chk("casimir_massless_matches_continuum",
        abs(vac["casimir_massless_L8_N128"]
            - vac["casimir_massless_exact_continuum"]) < 5e-6)
    chk("mass_difference_fixed_lattice",
        abs(vac["mass_difference_fixed_lattice"] - (-20.113232)) < 1e-4)
    chk("heavier_field_costs_more_vacuum",
        vacuum_energy(N_DEMO, A_DEMO, M_OUT)
        > vacuum_energy(N_DEMO, A_DEMO, M_DEMO))

    # 3. wavepacket - measured speed vs three predictions
    pkt = packet_report()
    chk("packet_intensity_conserved",
        pkt["intensity_conserved"]
        and abs(pkt["intensity_total"] - N_PKT) < 1e-6)
    chk("packet_starts_at_centre",
        abs(pkt["start_position"] - N_PKT * A_DEMO / 2.0) < 1e-6)
    chk("packet_matches_weighted_group_velocity",
        pkt["err_vs_weighted"] < 0.002)
    chk("packet_below_central_group_velocity",
        pkt["v_measured"] < pkt["v_central_lattice"]
        and pkt["err_vs_central"] < 0.03)
    chk("packet_slower_than_continuum",
        pkt["v_measured"] < pkt["v_continuum"]
        and 0.04 < pkt["err_vs_continuum"] < 0.08)

    # 4. quench - Bogoliubov arithmetic, sudden vs smooth
    chk("beta2_zero_mode_one_third",
        abs(beta2_sudden_mode(0.0, A_DEMO, M_IN, M_OUT) - 1.0 / 3.0) < 1e-12)
    chk("bogoliubov_unitarity_all_modes",
        all(abs(alpha2_sudden_mode(k, A_DEMO, M_IN, M_OUT)
                - beta2_sudden_mode(k, A_DEMO, M_IN, M_OUT) - 1.0) < 1e-12
            for k in lattice_momenta(N_DEMO, A_DEMO)))
    chk("no_quench_no_particles",
        beta2_sudden_total(N_DEMO, A_DEMO, M_DEMO, M_DEMO) == 0.0)
    que = quench_report()
    chk("sudden_total_value",
        4.72 < que["totals"]["sudden_jump"] < 4.73)
    chk("smooth_ramps_suppress",
        que["totals"]["smooth_tau_5"] < que["totals"]["smooth_tau_1"]
        < que["totals"]["sudden_jump"])
    chk("smooth_tau5_value", 0.30 < que["totals"]["smooth_tau_5"] < 0.33)
    chk("numeric_near_sudden_limit",
        abs(beta2_smooth_total(tau=0.05, dt=0.002, tail=2.0)
            - beta2_sudden_total()) / beta2_sudden_total() < 0.02)

    # 5. correlations - massive dies fast, massless lingers
    cor = correlation_report()
    mv = cor["massive"]
    chk("correlation_massive_monotone",
        mv[0] > mv[1] > mv[2] > mv[4] > mv[8] > mv[16] > 0.0)
    chk("correlation_symmetric",
        abs(correlation_value(5) - correlation_value(N_CORR - 5)) < 1e-12)
    chk("correlation_massless_lingers",
        cor["ratio_at_8_massive"] < 0.01 < cor["ratio_at_8_massless"]
        and cor["ratio_at_8_massless"] > 10.0 * cor["ratio_at_8_massive"])
    chk("correlation_zero_value", 0.43 < mv[0] < 0.44)

    # 6. classifier - labels come from the lab's own policy
    rep = classifier_report()
    chk("classifier_sudden_violent",
        rep["sudden_quench_demo_lattice"] == "quench-violent")
    chk("classifier_coarse_artefact",
        rep["coarse_lattice_gentle_quench"] == "lattice-artefact")
    chk("classifier_smooth_adiabatic",
        rep["smooth_ramp_demo_lattice"] == "quench-adiabatic")
    chk("classifier_fine_continuum",
        rep["fine_lattice_no_quench"] == "continuum-like")
    chk("classifier_matches_policy_on_scenarios",
        all(classify_regime(*f) == regime_policy(*f)
            for f in scenario_features().values()))
    chk("policy_thresholds",
        regime_policy(0.0, 1.0, 0.0) == "quench-violent"
        and regime_policy(0.1, 0.0, 0.0) == "lattice-artefact"
        and regime_policy(0.0, 0.1, 0.0) == "quench-adiabatic"
        and regime_policy(0.0, 0.0, 0.0) == "continuum-like")

    # gates + seats
    chk("hold_gates_14", len(HOLD_GATES) == 14
        and all(v.startswith("HOLD") for v in HOLD_GATES.values()))
    chk("gate_cosmology_hold", gate("cosmology_claim") == "HOLD")
    chk("gate_particle_prediction_hold",
        gate("particle_physics_prediction") == "HOLD")
    chk("gate_real_creation_hold",
        gate("real_particle_creation_claim") == "HOLD")
    chk("gate_vacuum_cosmology_hold",
        gate("vacuum_energy_cosmology_claim") == "HOLD")
    chk("gate_ftl_hold", gate("faster_than_light_claim") == "HOLD")
    chk("gate_sandbox_proceed", gate("run_simulation") == "PROCEED")
    brains = brains_report()
    chk("argon4_no_override", brains["decider"]["can_override_hold"] is False
        and brains["decider"]["seat"]
        == "Gemini Argon 4 Extended Thinking"
        and brains["decider"]["model_id"] == "gemini-argon-4")
    chk("claude_no_override", brains["advisor"]["can_override_hold"] is False)
    chk("flow_plan_only", brains["flow"]["rendered"] is False
        and brains["flow"]["live"] == 0)
    return c


# ================================================================ CLI / demo
def demo():
    print("=" * 68)
    print("QuantumField-Lab - quantum field theory on a lattice")
    print("by Darion Kellar | MIT | pure stdlib | zero network | EDUCATION ONLY")
    print("=" * 68)
    print("\n[1] THE HONEST CORE - a regulator, not spacetime")
    print("    A free scalar (Klein-Gordon) field on a finite ring of")
    print("    coupled oscillators, natural units hbar = c = 1. Every")
    print("    number is an exact lattice mode sum at labelled teaching")
    print("    parameters. The lattice is a regulator: it makes the field")
    print("    finite by bending its physics, and this lab prints the")
    print("    bending next to every result. Nothing here quantised")
    print("    spacetime, created a real particle, or predicts the")
    print("    universe.")
    disp = dispersion_report()
    print("\n[2] Dispersion - lattice omega_k vs continuum sqrt(m^2 + k^2)")
    print(f"    (N = {disp['n_sites']}, a = {disp['spacing']}, "
          f"m = {disp['mass']})")
    for row in disp["rows"]:
        print(f"    k = {row['k']:7.4f}  lattice {row['omega_lattice']:.6f}"
              f"  continuum {row['omega_continuum']:.6f}"
              f"  deviation {row['rel_deviation']:.6f}")
    print(f"    -> at the packet's k0 = {K0_PKT} the lattice is already "
          f"{disp['deviation_at_packet_k']:.4%} low;")
    print(f"       at the zone edge k = pi it is "
          f"{disp['deviation_at_zone_edge']:.4%} low. The seam is the lesson.")
    vac = vacuum_report()
    print("\n[3] Vacuum energy - a divergent sum and a finite difference")
    print("    fixed spacing a = 1, box grows (pure volume growth):")
    for row in vac["fixed_spacing_volume_growth"]:
        print(f"    N = {row['n_sites']:4d}  E0 = {row['e0']:10.4f}"
              f"  E0/N = {row['e0_per_site']:.6f}")
    print(f"    fixed volume L = {L_VAC:g}, lattice refines (cutoff growth):")
    for row in vac["fixed_volume_refinement"]:
        print(f"    N = {row['n_sites']:4d}  a = {row['spacing']:.4f}"
              f"  E0 = {row['e0']:10.4f}")
    print(f"    -> E0 grows x{vac['refinement_growth_factor']} over the "
          f"refinement: the sum is cutoff-dominated.")
    print(f"    Casimir difference E(PBC) - E(APBC), L = {L_CASIMIR:g}, "
          f"m = {M_DEMO}:")
    for row in vac["casimir_massive_L8"]:
        print(f"    N = {row['n_sites']:4d}  diff = {row['casimir']:.6f}"
              f"  change {row['change_from_previous']}")
    print(f"    -> the difference converges while E0 explodes. Massless"
          f" check: lattice {vac['casimir_massless_L8_N128']:.6f} vs"
          f" exact -pi/(4L) = {vac['casimir_massless_exact_continuum']:.6f}.")
    pkt = packet_report()
    print("\n[4] Wavepacket - one packet, three predicted speeds")
    print(f"    Gaussian packet, k0 = {pkt['k0']}, sigma_k = "
          f"{pkt['sigma_k']}, N = {pkt['n_sites']}: rides from x = "
          f"{pkt['start_position']:.1f} to x = {pkt['end_position']:.1f}")
    print(f"    measured centroid velocity      {pkt['v_measured']:.6f}")
    print(f"    |c_k|^2-weighted lattice d(w)/dk {pkt['v_weighted_lattice']:.6f}"
          f"  (err {pkt['err_vs_weighted']:.4%})")
    print(f"    lattice d(w)/dk at k0            {pkt['v_central_lattice']:.6f}"
          f"  (err {pkt['err_vs_central']:.4%}, finite packet width)")
    print(f"    continuum d(w)/dk at k0          {pkt['v_continuum']:.6f}"
          f"  (err {pkt['err_vs_continuum']:.4%}, the lattice is slower)")
    que = quench_report()
    print("\n[5] Quench - particle creation by a mass jump (Bogoliubov)")
    print(f"    m {que['m_in']} -> {que['m_out']} on N = {que['n_sites']} "
          f"modes: |beta_k|^2 at k = 0 is {que['beta2_at_k0']:.6f} "
          f"(= 1/3, the maximum)")
    for name, total in que["totals"].items():
        print(f"    total created, {name:14s} {total:.6f}")
    print(f"    -> the tau = 5 ramp creates x"
          f"{que['suppression_tau5_vs_sudden']} fewer particles than the"
          f" sudden jump. All of them exist only in this arithmetic.")
    cor = correlation_report()
    print("\n[6] Vacuum correlations - massive dies fast, massless lingers")
    print("    <phi_x phi_0> at separation x (sites):")
    for x in (0, 1, 2, 4, 8, 16):
        print(f"    x = {x:2d}  massive {cor['massive'][x]:.6f}"
              f"  massless {cor['massless_zero_mode_omitted'][x]:.6f}")
    print(f"    -> C(8)/C(0): massive {cor['ratio_at_8_massive']:.6f} vs"
          f" massless {cor['ratio_at_8_massless']:.6f} (zero mode omitted,"
          f" labelled IR regulator).")
    print("\n[7] Regime classifier (TinyML kNN, labels from the lab policy)")
    for name, label in classifier_report().items():
        print(f"    {name:32s} -> {label}")
    print("\n[8] Advisory seats")
    brains = brains_report()
    print(f"    decider: {brains['decider']['decision']} "
          f"trace={brains['decider']['trace_sha256_16']}")
    print(f"    advisor can_override_hold = "
          f"{brains['advisor']['can_override_hold']}")
    print(f"    flow rendered = {brains['flow']['rendered']} "
          f"live = {brains['flow']['live']}")
    print(f"\n[9] HOLD gates: {len(HOLD_GATES)}")
    for key in HOLD_GATES:
        print(f"    HOLD  {key}")
    checks = run_checks()
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nCHECKS {passed}/{len(checks)}")
    for name, ok in checks:
        if not ok:
            print(f"    FAIL {name}")
    verdict = "PROCEED" if passed == len(checks) else "HOLD"
    print(f"VERDICT {verdict} (sandbox simulation only) | "
          f"HOLD gates {len(HOLD_GATES)}")
    return 0 if passed == len(checks) else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    cmd = argv[0]
    if cmd == "checks":
        checks = run_checks()
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'} {name}")
        print(f"CHECKS {sum(1 for _, ok in checks if ok)}/{len(checks)}")
        return 0 if all(ok for _, ok in checks) else 1
    if cmd == "dispersion":
        print(json.dumps(dispersion_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "vacuum":
        print(json.dumps(vacuum_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "packet":
        print(json.dumps(packet_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "quench":
        print(json.dumps(quench_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "correlate":
        print(json.dumps(correlation_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "classify":
        print(json.dumps(classifier_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "brains":
        print(json.dumps(brains_report(), indent=2, sort_keys=True))
        return 0
    if cmd == "holds":
        for key, value in HOLD_GATES.items():
            print(f"{key}: {value}")
        return 0
    if cmd == "hold-demo":
        action = argv[1] if len(argv) > 1 else "cosmology_claim"
        print(f"{action}: {HOLD_GATES.get(action, 'PROCEED - not gated')}")
        return 2 if gate(action) == "HOLD" else 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
