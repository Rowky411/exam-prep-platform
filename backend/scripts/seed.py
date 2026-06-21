"""
Phase 1 seed script — loads ~300 questions into Postgres.

Run from inside the container:
    docker compose exec api python scripts/seed.py

Or locally (needs DATABASE_URL in env):
    DATABASE_URL=postgresql://examprep:examprep@localhost:5432/examprep python scripts/seed.py
"""

import asyncio
import json
import os
import sys
import uuid

import asyncpg

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://examprep:examprep@localhost:5432/examprep"
)


# ---------------------------------------------------------------------------
# Hand-crafted question templates
# Each entry is a dict matching the questions schema.
# ---------------------------------------------------------------------------

def _mcq(stem, options, correct_id, explanation, subject, chapter, topic, difficulty, exam_tag, qtype="single_mcq"):
    return {
        "type": qtype,
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "difficulty": difficulty,
        "exam_tag": exam_tag,
        "stem": stem,
        "options": options,
        "correct": {"id": correct_id} if qtype == "single_mcq" else correct_id,
        "explanation": explanation,
        "language": "en",
    }


def _tf(stem, correct, explanation, subject, chapter, topic, difficulty, exam_tag):
    return {
        "type": "true_false",
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "difficulty": difficulty,
        "exam_tag": exam_tag,
        "stem": stem,
        "options": [{"id": "true", "text": "True"}, {"id": "false", "text": "False"}],
        "correct": {"id": "true" if correct else "false"},
        "explanation": explanation,
        "language": "en",
    }


def _num(stem, value, explanation, subject, chapter, topic, difficulty, exam_tag, tolerance=0.01):
    return {
        "type": "numerical",
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "difficulty": difficulty,
        "exam_tag": exam_tag,
        "stem": stem,
        "options": None,
        "correct": {"value": value, "tolerance": tolerance},
        "explanation": explanation,
        "language": "en",
    }


def opts(*pairs):
    """opts('a','Text A', 'b','Text B', ...) → [{id,text}, ...]"""
    it = iter(pairs)
    return [{"id": k, "text": v} for k, v in zip(it, it)]


# ---------------------------------------------------------------------------
# PHYSICS — Mechanics
# ---------------------------------------------------------------------------

def physics_mechanics():
    P, CH = "Physics", "Mechanics"
    qs = []

    # Kinematics
    T = "Kinematics"
    qs += [
        _mcq(
            "A particle moves with uniform velocity $v = 15\\,\\text{m/s}$. "
            "The distance covered in $t = 4\\,\\text{s}$ is:",
            opts("a", "45 m", "b", "60 m", "c", "75 m", "d", "30 m"),
            "b",
            "$d = vt = 15 \\times 4 = 60\\,\\text{m}$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "A car starts from rest and accelerates uniformly. After $t = 5\\,\\text{s}$ "
            "its velocity is $20\\,\\text{m/s}$. The acceleration is:",
            opts("a", "$2\\,\\text{m/s}^2$", "b", "$4\\,\\text{m/s}^2$",
                 "c", "$5\\,\\text{m/s}^2$", "d", "$10\\,\\text{m/s}^2$"),
            "b",
            "$a = \\frac{v-u}{t} = \\frac{20-0}{5} = 4\\,\\text{m/s}^2$",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "A ball is thrown upward with initial velocity $u = 20\\,\\text{m/s}$. "
            "Taking $g = 10\\,\\text{m/s}^2$, find the maximum height (in metres).",
            20.0,
            "$H = \\frac{u^2}{2g} = \\frac{400}{20} = 20\\,\\text{m}$",
            P, CH, T, 2, "HSC",
        ),
        _num(
            "A stone is dropped from rest. Using $g = 10\\,\\text{m/s}^2$, find "
            "its velocity (m/s) after falling for $3\\,\\text{s}$.",
            30.0,
            "$v = gt = 10 \\times 3 = 30\\,\\text{m/s}$",
            P, CH, T, 1, "BCS",
        ),
        _tf(
            "An object in uniform circular motion has constant speed but changing velocity.",
            True,
            "Speed (magnitude) is constant; direction changes → velocity vector changes.",
            P, CH, T, 2, "HSC",
        ),
        _mcq(
            "The displacement-time graph of a body moving with constant acceleration is a:",
            opts("a", "Straight line", "b", "Parabola", "c", "Hyperbola", "d", "Circle"),
            "b",
            "$s = ut + \\frac{1}{2}at^2$ — quadratic in $t$, so a parabola.",
            P, CH, T, 2, "admission",
        ),
        _num(
            "A projectile is launched horizontally at $u = 30\\,\\text{m/s}$ from height "
            "$h = 45\\,\\text{m}$. Using $g = 10\\,\\text{m/s}^2$, find the horizontal "
            "range (in metres).",
            90.0,
            "Time of flight $t = \\sqrt{2h/g} = 3\\,\\text{s}$. Range $= ut = 90\\,\\text{m}$.",
            P, CH, T, 3, "admission",
        ),
        _mcq(
            "Two bodies are thrown vertically upward with the same speed from the same "
            "point at an interval of $2\\,\\text{s}$. They meet when the first body has "
            "been in flight for $t$ seconds. Which relation is correct? ($g = 10\\,\\text{m/s}^2$, $u = 25\\,\\text{m/s}$)",
            opts("a", "$t = 3\\,\\text{s}$", "b", "$t = 4\\,\\text{s}$",
                 "c", "$t = 3.5\\,\\text{s}$", "d", "$t = 2.5\\,\\text{s}$"),
            "c",
            "Setting heights equal: $ut - \\frac{1}{2}gt^2 = u(t-2) - \\frac{1}{2}g(t-2)^2$ → $t = 3.5\\,\\text{s}$.",
            P, CH, T, 4, "BCS",
        ),
    ]

    # Dynamics
    T = "Dynamics"
    qs += [
        _mcq(
            "A force $F = 50\\,\\text{N}$ acts on a body of mass $m = 10\\,\\text{kg}$. "
            "The acceleration produced is:",
            opts("a", "$2\\,\\text{m/s}^2$", "b", "$5\\,\\text{m/s}^2$",
                 "c", "$10\\,\\text{m/s}^2$", "d", "$500\\,\\text{m/s}^2$"),
            "b",
            "$a = F/m = 50/10 = 5\\,\\text{m/s}^2$ (Newton's second law).",
            P, CH, T, 1, "HSC",
        ),
        _tf(
            "Newton's third law states that action and reaction forces act on the same body.",
            False,
            "Action and reaction act on *different* bodies — they cannot cancel each other.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "A body of mass $5\\,\\text{kg}$ is on a frictionless horizontal surface. "
            "Two forces $F_1 = 10\\,\\text{N}$ and $F_2 = 4\\,\\text{N}$ act in opposite "
            "directions. The net acceleration is:",
            opts("a", "$1.2\\,\\text{m/s}^2$", "b", "$2.8\\,\\text{m/s}^2$",
                 "c", "$3.0\\,\\text{m/s}^2$", "d", "$2.0\\,\\text{m/s}^2$"),
            "a",
            "$a = (F_1 - F_2)/m = 6/5 = 1.2\\,\\text{m/s}^2$",
            P, CH, T, 2, "HSC",
        ),
        _num(
            "A $2\\,\\text{kg}$ block slides down a frictionless incline of angle "
            "$30°$. Using $g = 10\\,\\text{m/s}^2$, find the acceleration (m/s²).",
            5.0,
            "$a = g\\sin 30° = 10 \\times 0.5 = 5\\,\\text{m/s}^2$",
            P, CH, T, 2, "BCS",
        ),
        _mcq(
            "The coefficient of static friction between a block and a surface is $0.4$. "
            "The maximum static friction force on a $5\\,\\text{kg}$ block "
            "($g = 10\\,\\text{m/s}^2$) is:",
            opts("a", "10 N", "b", "20 N", "c", "40 N", "d", "2 N"),
            "b",
            "$f_s^{\\max} = \\mu_s N = 0.4 \\times 50 = 20\\,\\text{N}$",
            P, CH, T, 2, "admission",
        ),
        _mcq(
            "In a lift accelerating upward at $a$, the apparent weight of a person of "
            "mass $m$ is:",
            opts("a", "$mg$", "b", "$m(g-a)$", "c", "$m(g+a)$", "d", "$ma$"),
            "c",
            "Normal force $N = m(g+a)$ when lift accelerates upward.",
            P, CH, T, 3, "admission",
        ),
    ]

    # Energy & Work
    T = "Energy"
    qs += [
        _mcq(
            "Kinetic energy of a body of mass $m$ moving at velocity $v$ is:",
            opts("a", "$mv$", "b", "$\\frac{1}{2}mv^2$", "c", "$mv^2$", "d", "$2mv^2$"),
            "b",
            "$KE = \\frac{1}{2}mv^2$ — derived from work–energy theorem.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "A $4\\,\\text{kg}$ body moving at $6\\,\\text{m/s}$ is brought to rest "
            "by friction. Find the work done by friction (in J). Give a negative value.",
            -72.0,
            "$W = -\\Delta KE = -(0 - \\frac{1}{2} \\times 4 \\times 36) = -72\\,\\text{J}$",
            P, CH, T, 2, "HSC",
            tolerance=0.5,
        ),
        _mcq(
            "A spring of spring constant $k = 200\\,\\text{N/m}$ is compressed by "
            "$x = 0.1\\,\\text{m}$. Its elastic potential energy is:",
            opts("a", "1 J", "b", "2 J", "c", "20 J", "d", "0.1 J"),
            "a",
            "$PE = \\frac{1}{2}kx^2 = \\frac{1}{2} \\times 200 \\times 0.01 = 1\\,\\text{J}$",
            P, CH, T, 2, "BCS",
        ),
        _tf(
            "The work done by a conservative force around a closed path is always zero.",
            True,
            "By definition of conservative force — path-independence implies zero net work on closed loops.",
            P, CH, T, 3, "admission",
        ),
        _mcq(
            "Power is defined as:",
            opts("a", "Force × displacement", "b", "Work / time",
                 "c", "Force / time", "d", "Energy × time"),
            "b",
            "$P = W/t$ — rate of doing work.",
            P, CH, T, 1, "HSC",
        ),
    ]

    # Momentum
    T = "Momentum"
    qs += [
        _mcq(
            "A $3\\,\\text{kg}$ body moving at $4\\,\\text{m/s}$ collides with a "
            "$5\\,\\text{kg}$ body at rest. They stick together. Final velocity is:",
            opts("a", "$1\\,\\text{m/s}$", "b", "$1.5\\,\\text{m/s}$",
                 "c", "$2\\,\\text{m/s}$", "d", "$3\\,\\text{m/s}$"),
            "b",
            "Conservation of momentum: $(3)(4) = (3+5)v \\Rightarrow v = 12/8 = 1.5\\,\\text{m/s}$",
            P, CH, T, 2, "HSC",
        ),
        _tf(
            "In a perfectly elastic collision, both momentum and kinetic energy are conserved.",
            True,
            "Elastic collision by definition conserves KE; momentum is always conserved.",
            P, CH, T, 2, "HSC",
        ),
        _mcq(
            "Impulse equals:",
            opts("a", "Force × distance", "b", "Change in momentum",
                 "c", "Mass × acceleration", "d", "Work done"),
            "b",
            "$J = F \\Delta t = \\Delta p$ — impulse–momentum theorem.",
            P, CH, T, 1, "BCS",
        ),
        _num(
            "A $0.1\\,\\text{kg}$ ball hits a wall at $20\\,\\text{m/s}$ and rebounds "
            "at $20\\,\\text{m/s}$. Find the magnitude of change in momentum (kg·m/s).",
            4.0,
            "$|\\Delta p| = m|v_f - v_i| = 0.1 \\times |(-20) - 20| = 0.1 \\times 40 = 4\\,\\text{kg·m/s}$",
            P, CH, T, 2, "admission",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# PHYSICS — Thermodynamics
# ---------------------------------------------------------------------------

def physics_thermo():
    P, CH = "Physics", "Thermodynamics"
    qs = []

    T = "Ideal Gas"
    qs += [
        _mcq(
            "The ideal gas law is:",
            opts("a", "$PV = nRT$", "b", "$PV = nkT$", "c", "$P = \\rho RT$", "d", "$PV = RT$"),
            "a",
            "$PV = nRT$ where $n$ = moles, $R$ = universal gas constant.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "An ideal gas at $T = 300\\,\\text{K}$ and $P = 1\\,\\text{atm}$ occupies "
            "$V = 2\\,\\text{L}$. At $T = 600\\,\\text{K}$ and same pressure, "
            "the new volume (in L) is:",
            4.0,
            "At constant $P$: $V \\propto T$ → $V_2 = 2 \\times 600/300 = 4\\,\\text{L}$",
            P, CH, T, 2, "HSC",
        ),
        _tf(
            "At constant temperature, pressure and volume of an ideal gas are inversely proportional.",
            True,
            "Boyle's Law: $PV = \\text{const}$ at fixed $T$ → $P \\propto 1/V$.",
            P, CH, T, 1, "BCS",
        ),
        _mcq(
            "Which law states that at constant pressure, volume is proportional to temperature?",
            opts("a", "Boyle's Law", "b", "Charles' Law",
                 "c", "Gay-Lussac's Law", "d", "Avogadro's Law"),
            "b",
            "Charles' Law: $V/T = \\text{const}$ at fixed $P$.",
            P, CH, T, 1, "admission",
        ),
        _num(
            "A fixed amount of ideal gas at $27°\\text{C}$ has pressure $2\\,\\text{atm}$. "
            "At $127°\\text{C}$ (volume constant), the pressure (in atm) is:",
            round(2 * 400 / 300, 4),
            "$P \\propto T$ at fixed $V$: $P_2 = 2 \\times 400/300 \\approx 2.667\\,\\text{atm}$",
            P, CH, T, 2, "BCS",
            tolerance=0.01,
        ),
    ]

    T = "Laws of Thermodynamics"
    qs += [
        _mcq(
            "The first law of thermodynamics is essentially a statement of:",
            opts("a", "Conservation of momentum", "b", "Conservation of energy",
                 "c", "Conservation of mass", "d", "Conservation of charge"),
            "b",
            "$\\Delta U = Q - W$ — internal energy change = heat absorbed − work done.",
            P, CH, T, 1, "HSC",
        ),
        _tf(
            "In an adiabatic process, no heat is exchanged between the system and surroundings.",
            True,
            "Adiabatic: $Q = 0$ by definition → $\\Delta U = -W$.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "Entropy of an isolated system in a spontaneous process:",
            opts("a", "Decreases", "b", "Stays constant", "c", "Increases", "d", "Oscillates"),
            "c",
            "Second law of thermodynamics: entropy of an isolated system never decreases.",
            P, CH, T, 2, "BCS",
        ),
        _mcq(
            "The efficiency of a Carnot engine operating between $T_H = 500\\,\\text{K}$ "
            "and $T_C = 300\\,\\text{K}$ is:",
            opts("a", "40%", "b", "50%", "c", "60%", "d", "20%"),
            "a",
            "$\\eta = 1 - T_C/T_H = 1 - 300/500 = 0.4 = 40\\%$",
            P, CH, T, 3, "admission",
        ),
        _num(
            "A Carnot engine absorbs $Q_H = 1000\\,\\text{J}$ from a hot reservoir at "
            "$T_H = 500\\,\\text{K}$ and rejects heat to $T_C = 250\\,\\text{K}$. "
            "Work output (in J):",
            500.0,
            "$W = \\eta Q_H = (1 - 250/500) \\times 1000 = 500\\,\\text{J}$",
            P, CH, T, 3, "admission",
        ),
        _tf(
            "An isothermal process occurs at constant internal energy for an ideal gas.",
            True,
            "For ideal gas, $U$ depends only on $T$. Isothermal → $T$ constant → $\\Delta U = 0$.",
            P, CH, T, 3, "BCS",
        ),
    ]

    T = "Heat Transfer"
    qs += [
        _mcq(
            "Which mode of heat transfer does not require a medium?",
            opts("a", "Conduction", "b", "Convection", "c", "Radiation", "d", "All require medium"),
            "c",
            "Radiation travels as electromagnetic waves — no medium needed.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "Stefan–Boltzmann law states the radiated power is proportional to:",
            opts("a", "$T$", "b", "$T^2$", "c", "$T^3$", "d", "$T^4$"),
            "d",
            "$P = \\epsilon \\sigma A T^4$ — fourth power of absolute temperature.",
            P, CH, T, 2, "BCS",
        ),
        _tf(
            "Good absorbers of radiation are also good emitters.",
            True,
            "Kirchhoff's law of thermal radiation: absorptivity = emissivity at thermal equilibrium.",
            P, CH, T, 2, "admission",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# PHYSICS — Electromagnetism
# ---------------------------------------------------------------------------

def physics_em():
    P, CH = "Physics", "Electromagnetism"
    qs = []

    T = "Electrostatics"
    qs += [
        _mcq(
            "Coulomb's law for the force between two point charges $q_1$ and $q_2$ "
            "separated by distance $r$ is:",
            opts("a", "$F = k\\frac{q_1 q_2}{r}$", "b", "$F = k\\frac{q_1 q_2}{r^2}$",
                 "c", "$F = k\\frac{q_1 + q_2}{r^2}$", "d", "$F = k q_1 q_2 r^2$"),
            "b",
            "$F = k\\frac{q_1 q_2}{r^2}$ where $k = 9 \\times 10^9\\,\\text{N·m}^2/\\text{C}^2$.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Two charges of $+2\\,\\mu\\text{C}$ each are $0.1\\,\\text{m}$ apart. "
            "Find the force between them (in N). "
            "Use $k = 9 \\times 10^9\\,\\text{N·m}^2/\\text{C}^2$.",
            3.6,
            "$F = k q^2/r^2 = 9\\times10^9 \\times (2\\times10^{-6})^2 / 0.01 = 3.6\\,\\text{N}$",
            P, CH, T, 2, "HSC",
            tolerance=0.05,
        ),
        _mcq(
            "The electric field inside a hollow conducting sphere carrying charge is:",
            opts("a", "Maximum at centre", "b", "Uniform", "c", "Zero", "d", "Same as outside"),
            "c",
            "By Gauss's law — no enclosed charge inside the shell → $E = 0$.",
            P, CH, T, 2, "BCS",
        ),
        _tf(
            "Electric field lines can intersect each other.",
            False,
            "If they intersected, there would be two directions of force at one point — impossible.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "The work done in moving a charge $q$ through potential difference $V$ is:",
            opts("a", "$V/q$", "b", "$qV$", "c", "$q/V$", "d", "$q^2V$"),
            "b",
            "$W = qV$ — definition of electric potential difference.",
            P, CH, T, 1, "admission",
        ),
    ]

    T = "Circuits"
    qs += [
        _mcq(
            "Ohm's law relates current $I$, voltage $V$, and resistance $R$ as:",
            opts("a", "$V = IR$", "b", "$I = VR$", "c", "$R = VI$", "d", "$V = I/R$"),
            "a",
            "$V = IR$ — Ohm's law (valid for ohmic conductors at constant temperature).",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Three resistors $R_1 = 2\\,\\Omega$, $R_2 = 3\\,\\Omega$, $R_3 = 5\\,\\Omega$ "
            "are connected in series. Find total resistance (in $\\Omega$).",
            10.0,
            "$R_{\\text{total}} = R_1 + R_2 + R_3 = 2 + 3 + 5 = 10\\,\\Omega$",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Two resistors $R_1 = 6\\,\\Omega$ and $R_2 = 3\\,\\Omega$ are connected "
            "in parallel. Find equivalent resistance (in $\\Omega$).",
            2.0,
            "$1/R = 1/6 + 1/3 = 1/6 + 2/6 = 3/6 \\Rightarrow R = 2\\,\\Omega$",
            P, CH, T, 2, "HSC",
        ),
        _mcq(
            "Power dissipated in a resistor $R$ carrying current $I$ is:",
            opts("a", "$IR$", "b", "$I^2 R$", "c", "$I R^2$", "d", "$V/R$"),
            "b",
            "$P = I^2 R = V^2/R = VI$",
            P, CH, T, 1, "BCS",
        ),
        _tf(
            "In a parallel circuit, the voltage across each branch is the same.",
            True,
            "Parallel branches share the same two nodes → same potential difference.",
            P, CH, T, 1, "BCS",
        ),
        _mcq(
            "Kirchhoff's current law (KCL) states that at any node:",
            opts(
                "a", "Sum of voltages = 0",
                "b", "Sum of currents entering = sum leaving",
                "c", "Total resistance is constant",
                "d", "Power = voltage × resistance",
            ),
            "b",
            "KCL = conservation of charge: $\\sum I_{\\text{in}} = \\sum I_{\\text{out}}$",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Magnetism"
    qs += [
        _mcq(
            "The force on a charge $q$ moving with velocity $v$ in magnetic field $B$ is:",
            opts(
                "a", "$F = qvB$",
                "b", "$F = qvB\\sin\\theta$",
                "c", "$F = qB/v$",
                "d", "$F = qv/B$",
            ),
            "b",
            "$\\vec{F} = q\\vec{v} \\times \\vec{B}$ → magnitude $F = qvB\\sin\\theta$.",
            P, CH, T, 2, "HSC",
        ),
        _tf(
            "A magnetic field can do work on a moving charge.",
            False,
            "Magnetic force $\\perp$ velocity → no work done: $W = \\vec{F} \\cdot \\vec{d} = 0$.",
            P, CH, T, 3, "BCS",
        ),
        _mcq(
            "Faraday's law relates induced EMF to:",
            opts(
                "a", "Rate of change of electric flux",
                "b", "Rate of change of magnetic flux",
                "c", "Magnitude of magnetic field",
                "d", "Velocity of charge",
            ),
            "b",
            "$\\mathcal{E} = -\\frac{d\\Phi_B}{dt}$ — induced EMF = negative rate of change of magnetic flux.",
            P, CH, T, 2, "admission",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# PHYSICS — Optics
# ---------------------------------------------------------------------------

def physics_optics():
    P, CH = "Physics", "Optics"
    qs = []

    T = "Reflection"
    qs += [
        _tf(
            "The angle of incidence equals the angle of reflection for a plane mirror.",
            True,
            "Law of reflection: $\\theta_i = \\theta_r$, measured from the normal.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "A concave mirror with focal length $f = 10\\,\\text{cm}$ forms an image "
            "of an object at $30\\,\\text{cm}$. Image distance (using mirror formula) is:",
            opts("a", "10 cm", "b", "15 cm", "c", "20 cm", "d", "12 cm"),
            "b",
            "$1/v + 1/u = 1/f$ → $1/v = 1/10 - 1/30 = 2/30 \\Rightarrow v = 15\\,\\text{cm}$",
            P, CH, T, 3, "BCS",
        ),
    ]

    T = "Refraction"
    qs += [
        _mcq(
            "Snell's law of refraction is:",
            opts(
                "a", "$n_1 \\sin\\theta_1 = n_2 \\sin\\theta_2$",
                "b", "$n_1 \\cos\\theta_1 = n_2 \\cos\\theta_2$",
                "c", "$n_1 \\theta_1 = n_2 \\theta_2$",
                "d", "$n_1 / \\sin\\theta_1 = n_2 / \\sin\\theta_2$",
            ),
            "a",
            "$n_1 \\sin\\theta_1 = n_2 \\sin\\theta_2$ — derived from wave speed change at interface.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Light travels from air ($n=1$) into glass ($n=1.5$) at angle of incidence "
            "$30°$. Find the angle of refraction in degrees (to nearest integer).",
            19.0,
            "$\\sin\\theta_2 = \\sin 30° / 1.5 = 0.5/1.5 \\approx 0.333 \\Rightarrow \\theta_2 \\approx 19.5° \\approx 19°$",
            P, CH, T, 2, "admission",
            tolerance=1.0,
        ),
        _tf(
            "Total internal reflection can occur when light moves from a denser to a rarer medium.",
            True,
            "TIR requires the angle of incidence to exceed the critical angle, possible only in denser→rarer transition.",
            P, CH, T, 2, "HSC",
        ),
        _mcq(
            "The critical angle $\\theta_c$ for a medium of refractive index $n$ is:",
            opts(
                "a", "$\\sin^{-1}(n)$",
                "b", "$\\cos^{-1}(1/n)$",
                "c", "$\\sin^{-1}(1/n)$",
                "d", "$\\tan^{-1}(n)$",
            ),
            "c",
            "$\\sin\\theta_c = 1/n$ at the interface with air ($n=1$).",
            P, CH, T, 2, "BCS",
        ),
    ]

    T = "Lenses"
    qs += [
        _mcq(
            "The lens maker's equation for a thin lens is:",
            opts(
                "a", "$1/f = (n-1)(1/R_1 - 1/R_2)$",
                "b", "$1/f = (n+1)(1/R_1 + 1/R_2)$",
                "c", "$f = (n-1)(R_1 - R_2)$",
                "d", "$1/f = 1/R_1 + 1/R_2$",
            ),
            "a",
            "$1/f = (n-1)\\left(\\frac{1}{R_1} - \\frac{1}{R_2}\\right)$",
            P, CH, T, 3, "admission",
        ),
        _mcq(
            "A converging lens of focal length $f = 20\\,\\text{cm}$ is used as a magnifier. "
            "For maximum magnification (near-point $D = 25\\,\\text{cm}$):",
            opts("a", "$m = 1.25$", "b", "$m = 2.25$", "c", "$m = 5$", "d", "$m = 2$"),
            "b",
            "$m = 1 + D/f = 1 + 25/20 = 2.25$",
            P, CH, T, 3, "BCS",
        ),
        _tf(
            "A diverging lens always forms a virtual, erect, and diminished image.",
            True,
            "Diverging lens always gives virtual erect diminished image regardless of object position.",
            P, CH, T, 2, "HSC",
        ),
    ]

    T = "Wave Optics"
    qs += [
        _mcq(
            "In Young's double-slit experiment, fringe width $\\beta$ is:",
            opts(
                "a", "$\\beta = \\lambda D / d$",
                "b", "$\\beta = \\lambda d / D$",
                "c", "$\\beta = D / (\\lambda d)$",
                "d", "$\\beta = d / (\\lambda D)$",
            ),
            "a",
            "$\\beta = \\lambda D / d$ where $D$ = screen distance, $d$ = slit separation.",
            P, CH, T, 3, "admission",
        ),
        _tf(
            "Diffraction is more pronounced when the slit width is much larger than the wavelength.",
            False,
            "Diffraction is most pronounced when slit width ≈ wavelength. Large slits produce narrow diffraction patterns.",
            P, CH, T, 3, "BCS",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# PHYSICS — Modern Physics
# ---------------------------------------------------------------------------

def physics_modern():
    P, CH = "Physics", "Modern Physics"
    qs = []

    T = "Photoelectric Effect"
    qs += [
        _mcq(
            "The photoelectric effect is explained by treating light as:",
            opts("a", "Waves", "b", "Particles (photons)", "c", "Both", "d", "Neither"),
            "b",
            "Einstein's explanation (1905): photons of energy $E = hf$ eject electrons.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "The energy of a photon with frequency $f$ is:",
            opts("a", "$hf^2$", "b", "$h/f$", "c", "$hf$", "d", "$f/h$"),
            "c",
            "$E = hf$ where $h = 6.626 \\times 10^{-34}\\,\\text{J·s}$ (Planck's constant).",
            P, CH, T, 1, "HSC",
        ),
        _tf(
            "Increasing light intensity (at fixed frequency) increases the maximum kinetic energy of emitted electrons.",
            False,
            "Intensity increases the *number* of photoelectrons, not their KE. KE depends on frequency.",
            P, CH, T, 2, "BCS",
        ),
        _mcq(
            "The stopping potential in the photoelectric effect is proportional to:",
            opts(
                "a", "Intensity of light",
                "b", "Frequency of light",
                "c", "Square of frequency",
                "d", "Wavelength squared",
            ),
            "b",
            "$eV_s = hf - \\phi$ → $V_s \\propto f$ at fixed work function $\\phi$.",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Atomic Models"
    qs += [
        _mcq(
            "In Bohr's model, the radius of the $n$-th orbit of hydrogen is proportional to:",
            opts("a", "$n$", "b", "$n^2$", "c", "$1/n$", "d", "$1/n^2$"),
            "b",
            "$r_n = a_0 n^2$ where $a_0 = 0.529\\,\\text{Å}$ (Bohr radius).",
            P, CH, T, 2, "HSC",
        ),
        _num(
            "The energy of the ground state ($n=1$) of hydrogen is $-13.6\\,\\text{eV}$. "
            "Find the energy of the $n=2$ level (in eV).",
            -3.4,
            "$E_n = -13.6/n^2\\,\\text{eV}$ → $E_2 = -13.6/4 = -3.4\\,\\text{eV}$",
            P, CH, T, 2, "BCS",
            tolerance=0.05,
        ),
        _tf(
            "De Broglie's hypothesis states that matter particles can exhibit wave-like behaviour.",
            True,
            "$\\lambda = h/p$ — all matter has an associated de Broglie wavelength.",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Nuclear Physics"
    qs += [
        _mcq(
            "Which particle is emitted in beta-minus decay?",
            opts("a", "Proton", "b", "Neutron", "c", "Electron + antineutrino", "d", "Positron"),
            "c",
            "$\\beta^-$ decay: $n \\to p + e^- + \\bar{\\nu}_e$",
            P, CH, T, 2, "HSC",
        ),
        _tf(
            "The mass number $A$ is conserved in all radioactive decay processes.",
            True,
            "Mass number = protons + neutrons; conserved in $\\alpha$, $\\beta$, $\\gamma$ decay.",
            P, CH, T, 1, "BCS",
        ),
        _mcq(
            "Half-life of a radioactive isotope is the time for:",
            opts(
                "a", "All atoms to decay",
                "b", "Half the atoms to decay",
                "c", "Activity to double",
                "d", "Mass to halve then double",
            ),
            "b",
            "$t_{1/2}$: time for $N \\to N/2$. Activity also halves each half-life.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "A radioactive sample has half-life $T_{1/2} = 5\\,\\text{days}$. "
            "What fraction of the original activity remains after $15\\,\\text{days}$?",
            0.125,
            "15 days = 3 half-lives → $(1/2)^3 = 1/8 = 0.125$",
            P, CH, T, 2, "admission",
            tolerance=0.001,
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# MATHEMATICS — Algebra
# ---------------------------------------------------------------------------

def math_algebra():
    P, CH = "Mathematics", "Algebra"
    qs = []

    T = "Quadratics"
    qs += [
        _mcq(
            "The roots of $x^2 - 5x + 6 = 0$ are:",
            opts("a", "2 and 3", "b", "1 and 6", "c", "-2 and -3", "d", "2 and -3"),
            "a",
            "Factor: $(x-2)(x-3) = 0 \\Rightarrow x = 2, 3$.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "The discriminant of $2x^2 + 3x - 2 = 0$ is:",
            25.0,
            "$\\Delta = b^2 - 4ac = 9 + 16 = 25$",
            P, CH, T, 1, "HSC",
        ),
        _tf(
            "If the discriminant of a quadratic is negative, it has two complex conjugate roots.",
            True,
            "$\\Delta < 0 \\Rightarrow x = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}$ with imaginary part.",
            P, CH, T, 2, "admission",
        ),
        _mcq(
            "Sum of roots of $ax^2 + bx + c = 0$ is:",
            opts("a", "$b/a$", "b", "$-b/a$", "c", "$c/a$", "d", "$-c/a$"),
            "b",
            "By Vieta's formulas: sum of roots $= -b/a$.",
            P, CH, T, 2, "BCS",
        ),
        _mcq(
            "Product of roots of $3x^2 - 7x + 2 = 0$ is:",
            opts("a", "$7/3$", "b", "$-7/3$", "c", "$2/3$", "d", "$-2/3$"),
            "c",
            "Product of roots $= c/a = 2/3$.",
            P, CH, T, 2, "BCS",
        ),
    ]

    T = "Matrices"
    qs += [
        _mcq(
            "For a $2 \\times 2$ matrix $A = \\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}$, "
            "$\\det(A) = $",
            opts("a", "$ab - cd$", "b", "$ad - bc$", "c", "$ac - bd$", "d", "$ad + bc$"),
            "b",
            "$\\det(A) = ad - bc$.",
            P, CH, T, 1, "HSC",
        ),
        _tf(
            "A square matrix with determinant zero is called singular and has no inverse.",
            True,
            "$\\det(A) = 0 \\Rightarrow A^{-1}$ does not exist.",
            P, CH, T, 2, "BCS",
        ),
        _num(
            "Find $\\det\\begin{pmatrix} 3 & 1 \\\\ 2 & 4 \\end{pmatrix}$.",
            10.0,
            "$\\det = 3 \\times 4 - 1 \\times 2 = 12 - 2 = 10$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "If $A$ is an $m \\times n$ matrix and $B$ is $n \\times p$, then $AB$ is:",
            opts("a", "$m \\times p$", "b", "$n \\times n$", "c", "$m \\times n$", "d", "$n \\times p$"),
            "a",
            "Matrix multiplication: $(m \\times n)(n \\times p) = m \\times p$.",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Sequences and Series"
    qs += [
        _num(
            "Find the sum of the first 10 terms of the arithmetic series: $2, 5, 8, \\ldots$",
            155.0,
            "$S_{10} = \\frac{10}{2}(2a + 9d) = 5(4 + 27) = 5 \\times 31 = 155$",
            P, CH, T, 2, "HSC",
        ),
        _mcq(
            "The $n$-th term of a geometric sequence with first term $a$ and ratio $r$ is:",
            opts("a", "$a + (n-1)r$", "b", "$ar^n$", "c", "$ar^{n-1}$", "d", "$a(n-1)r$"),
            "c",
            "$T_n = ar^{n-1}$",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Sum of infinite geometric series with $a = 3$ and $r = 1/3$:",
            4.5,
            "$S_\\infty = \\frac{a}{1-r} = \\frac{3}{2/3} = 4.5$",
            P, CH, T, 3, "BCS",
            tolerance=0.01,
        ),
        _tf(
            "An infinite geometric series converges if and only if $|r| < 1$.",
            True,
            "Convergence condition: $|r| < 1$ → $S_\\infty = a/(1-r)$.",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Polynomials"
    qs += [
        _mcq(
            "By the remainder theorem, the remainder when $f(x) = x^3 - 2x + 1$ is divided by $(x-2)$ is:",
            opts("a", "3", "b", "5", "c", "7", "d", "1"),
            "b",
            "$f(2) = 8 - 4 + 1 = 5$",
            P, CH, T, 2, "HSC",
        ),
        _tf(
            "$(x - a)$ is a factor of $f(x)$ if and only if $f(a) = 0$.",
            True,
            "Factor theorem: $f(a) = 0 \\Leftrightarrow (x-a)$ divides $f(x)$ with zero remainder.",
            P, CH, T, 2, "BCS",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# MATHEMATICS — Calculus
# ---------------------------------------------------------------------------

def math_calculus():
    P, CH = "Mathematics", "Calculus"
    qs = []

    T = "Limits"
    qs += [
        _num(
            r"Evaluate $\lim_{x \to 2} (3x^2 - x + 1)$.",
            11.0,
            "$3(4) - 2 + 1 = 11$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            r"$\lim_{x \to 0} \frac{\sin x}{x} = $",
            opts("a", "0", "b", "$\\infty$", "c", "1", "d", "undefined"),
            "c",
            "Standard limit: $\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1$.",
            P, CH, T, 2, "BCS",
        ),
        _tf(
            r"$\lim_{x \to \infty} \frac{1}{x} = 0$",
            True,
            "$1/x \\to 0$ as $x \\to \\infty$.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            r"$\lim_{x \to 0} \frac{e^x - 1}{x} = $",
            opts("a", "0", "b", "1", "c", "$e$", "d", "undefined"),
            "b",
            "Standard limit (or L'Hôpital): $\\frac{d}{dx}e^x\\big|_{x=0} = 1$.",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Derivatives"
    qs += [
        _mcq(
            r"$\frac{d}{dx}(x^n) = $",
            opts("a", "$nx^{n+1}$", "b", "$x^{n-1}$", "c", "$nx^{n-1}$", "d", "$(n-1)x^n$"),
            "c",
            "Power rule: $\\frac{d}{dx} x^n = nx^{n-1}$.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            r"Find $f'(x)$ at $x = 2$ for $f(x) = x^3 - 4x$.",
            8.0,
            "$f'(x) = 3x^2 - 4 \\Rightarrow f'(2) = 12 - 4 = 8$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            r"$\frac{d}{dx}(\sin x) = $",
            opts("a", "$-\\sin x$", "b", "$\\cos x$", "c", "$-\\cos x$", "d", "$\\tan x$"),
            "b",
            "$\\frac{d}{dx}\\sin x = \\cos x$",
            P, CH, T, 1, "BCS",
        ),
        _mcq(
            r"By the chain rule, $\frac{d}{dx}[\sin(x^2)] = $",
            opts(
                "a", "$\\cos(x^2)$",
                "b", "$2x\\cos(x^2)$",
                "c", "$2x\\sin(x^2)$",
                "d", "$-2x\\cos(x^2)$",
            ),
            "b",
            "Chain rule: $\\frac{d}{dx}\\sin(u) \\cdot \\frac{du}{dx} = \\cos(x^2) \\cdot 2x$.",
            P, CH, T, 2, "HSC",
        ),
        _num(
            r"Find the derivative of $f(x) = e^{3x}$ at $x = 0$.",
            3.0,
            "$f'(x) = 3e^{3x} \\Rightarrow f'(0) = 3$",
            P, CH, T, 2, "BCS",
        ),
        _mcq(
            r"If $f(x) = x^2 e^x$, then $f'(x) = $",
            opts(
                "a", "$2xe^x$",
                "b", "$x^2 e^x$",
                "c", "$e^x(2x + x^2)$",
                "d", "$e^x(x^2 - 2x)$",
            ),
            "c",
            "Product rule: $(x^2)' e^x + x^2 (e^x)' = 2xe^x + x^2 e^x = e^x(2x+x^2)$.",
            P, CH, T, 2, "admission",
        ),
        _tf(
            "A function has a local minimum at $x = a$ if $f'(a) = 0$ and $f''(a) > 0$.",
            True,
            "Second derivative test: $f'=0$ and $f''>0$ → local minimum.",
            P, CH, T, 3, "BCS",
        ),
    ]

    T = "Integrals"
    qs += [
        _mcq(
            r"$\int x^n \, dx = $ (where $n \neq -1$)",
            opts(
                "a", "$nx^{n-1} + C$",
                "b", "$\\frac{x^{n+1}}{n+1} + C$",
                "c", "$\\frac{x^{n-1}}{n-1} + C$",
                "d", "$x^{n+1} + C$",
            ),
            "b",
            "$\\int x^n\\,dx = \\frac{x^{n+1}}{n+1} + C$",
            P, CH, T, 1, "HSC",
        ),
        _num(
            r"Evaluate $\int_0^2 (3x^2 + 2x)\,dx$.",
            12.0,
            "$[x^3 + x^2]_0^2 = (8 + 4) - 0 = 12$",
            P, CH, T, 2, "HSC",
        ),
        _mcq(
            r"$\int e^x \, dx = $",
            opts("a", "$e^x / x + C$", "b", "$xe^x + C$", "c", "$e^x + C$", "d", "$e^{x+1} + C$"),
            "c",
            "$\\int e^x\\,dx = e^x + C$",
            P, CH, T, 1, "BCS",
        ),
        _num(
            r"Find the area under $f(x) = \sin x$ from $0$ to $\pi$.",
            2.0,
            "$\\int_0^\\pi \\sin x\\,dx = [-\\cos x]_0^\\pi = 1 + 1 = 2$",
            P, CH, T, 2, "admission",
            tolerance=0.01,
        ),
        _mcq(
            r"$\int \frac{1}{x}\,dx = $",
            opts("a", "$x^{-2} + C$", "b", "$\\ln|x| + C$", "c", "$-x^{-2} + C$", "d", "$e^x + C$"),
            "b",
            "$\\int \\frac{1}{x}\\,dx = \\ln|x| + C$",
            P, CH, T, 2, "HSC",
        ),
        _tf(
            r"$\int_a^b f(x)\,dx = -\int_b^a f(x)\,dx$",
            True,
            "Reversing limits negates the integral.",
            P, CH, T, 1, "BCS",
        ),
    ]

    T = "Applications of Calculus"
    qs += [
        _mcq(
            "The rate of change of a quantity $Q$ with respect to time is given by $\\frac{dQ}{dt}$. "
            "If $Q = 5t^2 - 3t$, the rate at $t = 2$ is:",
            opts("a", "11", "b", "14", "c", "17", "d", "7"),
            "c",
            "$dQ/dt = 10t - 3 \\Rightarrow$ at $t=2$: $20 - 3 = 17$",
            P, CH, T, 2, "admission",
        ),
        _num(
            "A rectangle has perimeter $40\\,\\text{m}$. Find the maximum area (in m²).",
            100.0,
            "Let side = $x$. Area $= x(20-x)$. Max at $x = 10$ → area $= 100\\,\\text{m}^2$.",
            P, CH, T, 3, "BCS",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# MATHEMATICS — Geometry
# ---------------------------------------------------------------------------

def math_geometry():
    P, CH = "Mathematics", "Geometry"
    qs = []

    T = "Triangles"
    qs += [
        _mcq(
            "The sum of interior angles of a triangle is:",
            opts("a", "$90°$", "b", "$180°$", "c", "$270°$", "d", "$360°$"),
            "b",
            "Angle sum property of a triangle.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "In a right triangle with legs $3$ and $4$, find the hypotenuse.",
            5.0,
            "$c = \\sqrt{3^2 + 4^2} = \\sqrt{25} = 5$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "Area of a triangle with base $b$ and height $h$ is:",
            opts("a", "$bh$", "b", "$\\frac{1}{2}bh$", "c", "$2bh$", "d", "$b^2h$"),
            "b",
            "$A = \\frac{1}{2}bh$",
            P, CH, T, 1, "BCS",
        ),
        _tf(
            "In any triangle, the exterior angle equals the sum of the two non-adjacent interior angles.",
            True,
            "Exterior angle theorem.",
            P, CH, T, 2, "HSC",
        ),
        _num(
            "Using Heron's formula, find the area of a triangle with sides $a = 5$, $b = 12$, $c = 13$.",
            30.0,
            "$s = 15$. $A = \\sqrt{15 \\cdot 10 \\cdot 3 \\cdot 2} = \\sqrt{900} = 30$",
            P, CH, T, 3, "admission",
        ),
    ]

    T = "Circles"
    qs += [
        _mcq(
            "The circumference of a circle of radius $r$ is:",
            opts("a", "$\\pi r^2$", "b", "$2\\pi r$", "c", "$4\\pi r$", "d", "$\\pi r$"),
            "b",
            "$C = 2\\pi r$",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Find the area of a circle with radius $r = 7\\,\\text{cm}$. Use $\\pi \\approx 22/7$.",
            154.0,
            "$A = \\pi r^2 = \\frac{22}{7} \\times 49 = 154\\,\\text{cm}^2$",
            P, CH, T, 1, "BCS",
        ),
        _tf(
            "The angle subtended by an arc at the centre is twice the angle subtended at any point on the remaining arc.",
            True,
            "Central angle theorem / inscribed angle theorem.",
            P, CH, T, 2, "admission",
        ),
        _mcq(
            "A tangent to a circle is perpendicular to the radius at the point of tangency.",
            opts("a", "True only for unit circles", "b", "False", "c", "True always", "d", "True only if the circle has integer radius"),
            "c",
            "Fundamental theorem: tangent ⊥ radius at point of contact.",
            P, CH, T, 2, "BCS",
        ),
    ]

    T = "Coordinate Geometry"
    qs += [
        _mcq(
            "Distance between points $(x_1, y_1)$ and $(x_2, y_2)$ is:",
            opts(
                "a", "$\\sqrt{(x_2-x_1) + (y_2-y_1)}$",
                "b", "$\\sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$",
                "c", "$(x_2-x_1)^2 + (y_2-y_1)^2$",
                "d", "$|x_2-x_1| + |y_2-y_1|$",
            ),
            "b",
            "Distance formula from Pythagoras.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Find the distance between $(1, 2)$ and $(4, 6)$.",
            5.0,
            "$d = \\sqrt{9 + 16} = \\sqrt{25} = 5$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "The slope of line joining $(2, 3)$ and $(5, 9)$ is:",
            opts("a", "1", "b", "2", "c", "3", "d", "0.5"),
            "b",
            "$m = (9-3)/(5-2) = 6/3 = 2$",
            P, CH, T, 1, "BCS",
        ),
        _mcq(
            "The equation of a line with slope $m$ passing through $(x_1, y_1)$ is:",
            opts(
                "a", "$y = mx + c$",
                "b", "$y - y_1 = m(x - x_1)$",
                "c", "$y + y_1 = m(x + x_1)$",
                "d", "$y = m(x + x_1)$",
            ),
            "b",
            "Point-slope form: $y - y_1 = m(x - x_1)$.",
            P, CH, T, 1, "admission",
        ),
        _tf(
            "Two lines with slopes $m_1$ and $m_2$ are perpendicular if $m_1 m_2 = -1$.",
            True,
            "Perpendicularity condition for non-vertical lines.",
            P, CH, T, 2, "HSC",
        ),
    ]

    T = "Vectors"
    qs += [
        _mcq(
            "The dot product $\\vec{A} \\cdot \\vec{B} = $",
            opts(
                "a", "$|A||B|\\sin\\theta$",
                "b", "$|A||B|\\cos\\theta$",
                "c", "$|A|\\cdot|B|$",
                "d", "$|A|+|B|$",
            ),
            "b",
            "$\\vec{A} \\cdot \\vec{B} = |A||B|\\cos\\theta$",
            P, CH, T, 2, "BCS",
        ),
        _tf(
            "The cross product of two parallel vectors is the zero vector.",
            True,
            "$\\vec{A} \\times \\vec{B} = |A||B|\\sin\\theta\\,\\hat{n}$; parallel → $\\theta = 0$ → $\\sin 0 = 0$.",
            P, CH, T, 2, "admission",
        ),
        _num(
            "Find the magnitude of $\\vec{v} = 3\\hat{i} + 4\\hat{j}$.",
            5.0,
            "$|\\vec{v}| = \\sqrt{9 + 16} = 5$",
            P, CH, T, 1, "HSC",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# MATHEMATICS — Statistics & Probability
# ---------------------------------------------------------------------------

def math_stats():
    P, CH = "Mathematics", "Statistics"
    qs = []

    T = "Descriptive Statistics"
    qs += [
        _num(
            "Find the mean of: $4, 7, 13, 16$.",
            10.0,
            "$\\bar{x} = (4+7+13+16)/4 = 40/4 = 10$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "The median of $\\{3, 7, 9, 11, 15\\}$ is:",
            opts("a", "7", "b", "9", "c", "11", "d", "10"),
            "b",
            "Middle value of sorted list of 5: $9$.",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "Find the variance of $\\{2, 4, 4, 4, 5, 5, 7, 9\\}$. (Population variance.)",
            4.0,
            "Mean $= 5$. $\\sigma^2 = \\frac{(9+1+1+1+0+0+4+16)}{8} = \\frac{32}{8} = 4$",
            P, CH, T, 3, "BCS",
            tolerance=0.01,
        ),
        _tf(
            "Standard deviation is the square root of variance.",
            True,
            "$\\sigma = \\sqrt{\\sigma^2}$",
            P, CH, T, 1, "HSC",
        ),
    ]

    T = "Probability"
    qs += [
        _mcq(
            "The probability of getting a head when flipping a fair coin is:",
            opts("a", "0", "b", "1", "c", "0.5", "d", "0.25"),
            "c",
            "$P(H) = 1/2 = 0.5$",
            P, CH, T, 1, "HSC",
        ),
        _num(
            "A bag has 3 red and 5 blue balls. Probability of drawing a red ball:",
            0.375,
            "$P = 3/8 = 0.375$",
            P, CH, T, 1, "BCS",
            tolerance=0.001,
        ),
        _mcq(
            "For mutually exclusive events $A$ and $B$, $P(A \\cup B) = $",
            opts(
                "a", "$P(A) \\cdot P(B)$",
                "b", "$P(A) + P(B) - P(A \\cap B)$",
                "c", "$P(A) + P(B)$",
                "d", "$P(A) - P(B)$",
            ),
            "c",
            "Mutually exclusive: $P(A \\cap B) = 0$ → $P(A \\cup B) = P(A) + P(B)$.",
            P, CH, T, 2, "HSC",
        ),
        _tf(
            "For independent events $A$ and $B$, $P(A \\cap B) = P(A) \\cdot P(B)$.",
            True,
            "Definition of independence.",
            P, CH, T, 2, "BCS",
        ),
        _num(
            "Two dice are rolled. Find the probability of getting a sum of 7.",
            round(6/36, 6),
            "Favourable: $(1,6),(2,5),(3,4),(4,3),(5,2),(6,1)$ = 6 outcomes. $P = 6/36 = 1/6$.",
            P, CH, T, 2, "admission",
            tolerance=0.001,
        ),
        _mcq(
            "Bayes' theorem relates $P(A|B)$ to:",
            opts(
                "a", "$P(B|A)$ and $P(A)$",
                "b", "$P(A)$ alone",
                "c", "$P(B)$ alone",
                "d", "$P(A) - P(B)$",
            ),
            "a",
            "$P(A|B) = \\frac{P(B|A) P(A)}{P(B)}$",
            P, CH, T, 3, "BCS",
        ),
    ]

    T = "Distributions"
    qs += [
        _mcq(
            "In a binomial distribution $B(n, p)$, the mean is:",
            opts("a", "$np(1-p)$", "b", "$np$", "c", "$n/p$", "d", "$p/n$"),
            "b",
            "$\\mu = np$",
            P, CH, T, 2, "admission",
        ),
        _mcq(
            "The standard normal distribution has mean and standard deviation:",
            opts("a", "0 and 1", "b", "1 and 0", "c", "0 and 0", "d", "1 and 1"),
            "a",
            "$Z \\sim N(0, 1)$: mean 0, SD 1.",
            P, CH, T, 2, "BCS",
        ),
        _tf(
            "The total area under a probability density function equals 1.",
            True,
            "Normalisation condition for any PDF.",
            P, CH, T, 1, "HSC",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# MATHEMATICS — Trigonometry
# ---------------------------------------------------------------------------

def math_trig():
    P, CH = "Mathematics", "Trigonometry"
    qs = []

    T = "Identities"
    qs += [
        _tf(
            "$\\sin^2\\theta + \\cos^2\\theta = 1$ for all $\\theta$.",
            True,
            "Pythagorean identity — fundamental in trigonometry.",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "$\\tan\\theta = $",
            opts("a", "$\\sin\\theta / \\cos\\theta$", "b", "$\\cos\\theta / \\sin\\theta$",
                 "c", "$1 / \\sin\\theta$", "d", "$1 / \\cos\\theta$"),
            "a",
            "$\\tan\\theta = \\sin\\theta / \\cos\\theta$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "$1 + \\tan^2\\theta = $",
            opts("a", "$\\sec^2\\theta$", "b", "$\\csc^2\\theta$", "c", "$\\cos^2\\theta$", "d", "1"),
            "a",
            "Derived from $\\sin^2 + \\cos^2 = 1$ by dividing by $\\cos^2$.",
            P, CH, T, 2, "BCS",
        ),
        _mcq(
            "$\\sin(A + B) = $",
            opts(
                "a", "$\\sin A \\cos B + \\cos A \\sin B$",
                "b", "$\\sin A \\cos B - \\cos A \\sin B$",
                "c", "$\\sin A \\sin B + \\cos A \\cos B$",
                "d", "$\\sin A \\sin B - \\cos A \\cos B$",
            ),
            "a",
            "Sum formula for sine.",
            P, CH, T, 2, "HSC",
        ),
        _mcq(
            "$\\cos 2\\theta = $",
            opts(
                "a", "$2\\sin\\theta\\cos\\theta$",
                "b", "$\\cos^2\\theta - \\sin^2\\theta$",
                "c", "$\\sin^2\\theta - \\cos^2\\theta$",
                "d", "$2\\cos^2\\theta + 1$",
            ),
            "b",
            "Double angle: $\\cos 2\\theta = \\cos^2\\theta - \\sin^2\\theta$ (also $= 2\\cos^2\\theta - 1 = 1 - 2\\sin^2\\theta$).",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Equations"
    qs += [
        _num(
            "Find the principal value of $\\sin^{-1}(1/2)$ in degrees.",
            30.0,
            "$\\sin 30° = 1/2 \\Rightarrow \\sin^{-1}(1/2) = 30°$",
            P, CH, T, 1, "HSC",
        ),
        _mcq(
            "General solution of $\\sin\\theta = 0$ is:",
            opts(
                "a", "$\\theta = n\\pi, n \\in \\mathbb{Z}$",
                "b", "$\\theta = 2n\\pi$",
                "c", "$\\theta = (2n+1)\\pi/2$",
                "d", "$\\theta = n\\pi/2$",
            ),
            "a",
            "$\\sin\\theta = 0 \\Rightarrow \\theta = n\\pi$.",
            P, CH, T, 2, "BCS",
        ),
        _mcq(
            "In triangle $ABC$, by the sine rule:",
            opts(
                "a", "$\\frac{a}{\\sin A} = \\frac{b}{\\sin B} = \\frac{c}{\\sin C}$",
                "b", "$a\\sin A = b\\sin B$",
                "c", "$\\frac{\\sin A}{a} = \\frac{\\sin B}{b} + \\frac{\\sin C}{c}$",
                "d", "$a + b = c\\sin C$",
            ),
            "a",
            "Sine rule: $a/\\sin A = b/\\sin B = c/\\sin C = 2R$ (circumradius).",
            P, CH, T, 2, "admission",
        ),
    ]

    T = "Applications"
    qs += [
        _num(
            "A ladder of length $5\\,\\text{m}$ leans against a wall at angle $60°$ to the ground. "
            "Height reached on wall (in m):",
            round(5 * (3**0.5) / 2, 4),
            "$h = 5\\sin 60° = 5 \\times \\frac{\\sqrt{3}}{2} \\approx 4.330\\,\\text{m}$",
            P, CH, T, 2, "HSC",
            tolerance=0.01,
        ),
        _mcq(
            "The angle of elevation of a tower top from a point $100\\,\\text{m}$ away "
            "is $30°$. Height of tower:",
            opts(
                "a", "$100/\\sqrt{3}\\,\\text{m}$",
                "b", "$100\\sqrt{3}\\,\\text{m}$",
                "c", "$50\\,\\text{m}$",
                "d", "$100\\,\\text{m}$",
            ),
            "a",
            "$\\tan 30° = h/100 \\Rightarrow h = 100\\tan 30° = 100/\\sqrt{3}\\,\\text{m}$.",
            P, CH, T, 2, "BCS",
        ),
        _tf(
            "The cosine rule is $c^2 = a^2 + b^2 - 2ab\\cos C$.",
            True,
            "Law of cosines — generalises Pythagoras when $C = 90°$ gives $c^2 = a^2 + b^2$.",
            P, CH, T, 2, "admission",
        ),
        _num(
            "In triangle $ABC$: $a = 7$, $b = 8$, $C = 60°$. Find $c^2$.",
            57.0,
            "$c^2 = 49 + 64 - 2(7)(8)(0.5) = 113 - 56 = 57$",
            P, CH, T, 3, "HSC",
        ),
    ]

    return qs


# ---------------------------------------------------------------------------
# Programmatic fill-up to reach ~300
# ---------------------------------------------------------------------------

def generate_kinematics_numericals():
    """Generate parametric kinematics problems to fill up question count."""
    qs = []
    configs = [
        # (u, a, t, exam_tag, difficulty)
        (0, 3, 4, "HSC", 1),
        (0, 5, 6, "BCS", 1),
        (10, 2, 5, "HSC", 2),
        (5, 4, 3, "admission", 2),
        (0, 9.8, 3, "BCS", 2),
        (20, -5, 2, "HSC", 3),
        (15, -3, 4, "admission", 3),
        (0, 2.5, 8, "BCS", 2),
        (8, 3, 6, "HSC", 2),
        (12, -4, 2, "admission", 3),
        (0, 10, 5, "BCS", 1),
        (25, -5, 3, "HSC", 3),
    ]
    for u, a, t, tag, diff in configs:
        v = u + a * t
        qs.append(_num(
            f"A body starts with initial velocity $u = {u}\\,\\text{{m/s}}$ and acceleration "
            f"$a = {a}\\,\\text{{m/s}}^2$. Find velocity after $t = {t}\\,\\text{{s}}$ (in m/s).",
            float(v),
            f"$v = u + at = {u} + ({a})({t}) = {v}\\,\\text{{m/s}}$",
            "Physics", "Mechanics", "Kinematics", diff, tag,
        ))
        s = u * t + 0.5 * a * t * t
        qs.append(_num(
            f"A body with $u = {u}\\,\\text{{m/s}}$ and $a = {a}\\,\\text{{m/s}}^2$. "
            f"Find displacement in $t = {t}\\,\\text{{s}}$ (in m).",
            float(s),
            f"$s = ut + \\frac{{1}}{{2}}at^2 = {u}({t}) + 0.5({a})({t}^2) = {s}\\,\\text{{m}}$",
            "Physics", "Mechanics", "Kinematics", diff, tag,
            tolerance=0.1,
        ))
    return qs


def generate_circuit_numericals():
    qs = []
    configs = [
        # (V, R, tag, diff)
        (12, 4, "HSC", 1),
        (24, 8, "BCS", 1),
        (9, 3, "admission", 1),
        (120, 60, "HSC", 2),
        (5, 0.5, "BCS", 2),
        (48, 16, "admission", 2),
    ]
    for V, R, tag, diff in configs:
        I = V / R
        qs.append(_num(
            f"A resistor $R = {R}\\,\\Omega$ is connected to voltage $V = {V}\\,\\text{{V}}$. "
            f"Find the current (in A).",
            float(I),
            f"$I = V/R = {V}/{R} = {I}\\,\\text{{A}}$",
            "Physics", "Electromagnetism", "Circuits", diff, tag,
            tolerance=0.01,
        ))
        P = V * I
        qs.append(_num(
            f"A $R = {R}\\,\\Omega$ resistor carries $I = {I}\\,\\text{{A}}$. Power dissipated (in W):",
            float(P),
            f"$P = I^2 R = {I}^2 \\times {R} = {P}\\,\\text{{W}}$",
            "Physics", "Electromagnetism", "Circuits", diff, tag,
            tolerance=0.1,
        ))
    return qs


def generate_algebra_numericals():
    qs = []
    # Quadratic roots
    configs = [
        # (a, b, c, r1, r2, tag, diff)
        (1, -7, 12, 3, 4, "HSC", 2),
        (1, -10, 24, 4, 6, "BCS", 2),
        (2, -5, 2, 0.5, 2, "admission", 3),
        (1, -6, 8, 2, 4, "HSC", 2),
        (3, -7, 2, 1/3, 2, "BCS", 3),
    ]
    for a, b, c, r1, r2, tag, diff in configs:
        qs.append(_mcq(
            f"Solve ${'x^2' if a == 1 else f'{a}x^2'} {'+ ' + str(b) + 'x' if b >= 0 else str(b) + 'x'} "
            f"{'+ ' + str(c) if c >= 0 else str(c)} = 0$.",
            opts("a", f"${r1}$ and ${r2}$",
                 "b", f"$-{r1}$ and $-{r2}$",
                 "c", f"${r1}$ and $-{r2}$",
                 "d", f"$-{r1}$ and ${r2}$"),
            "a",
            f"Roots by factoring or quadratic formula: $x = {r1}, {r2}$.",
            "Mathematics", "Algebra", "Quadratics", diff, tag,
        ))

    # Arithmetic series sums
    ap_configs = [
        # (a, d, n, tag, diff)
        (1, 1, 10, "HSC", 1),
        (3, 4, 8, "BCS", 2),
        (5, 3, 12, "admission", 2),
        (2, 6, 6, "HSC", 2),
        (10, 5, 5, "BCS", 1),
        (1, 2, 20, "admission", 2),
    ]
    for a, d, n, tag, diff in ap_configs:
        S = n * (2 * a + (n - 1) * d) // 2
        qs.append(_num(
            f"Find the sum of the first $n = {n}$ terms of the AP with "
            f"first term $a = {a}$ and common difference $d = {d}$.",
            float(S),
            f"$S_n = \\frac{{n}}{{2}}(2a + (n-1)d) = \\frac{{{n}}}{{2}}({2*a} + {n-1} \\times {d}) = {S}$",
            "Mathematics", "Algebra", "Sequences and Series", diff, tag,
        ))

    return qs


def generate_calculus_numericals():
    qs = []
    # Derivative evaluations
    configs = [
        # (expr_str, deriv_at, val, explanation, diff, tag)
        ("$f(x) = 4x^3$", "x=1", 12.0, "$f'(x) = 12x^2 \\Rightarrow f'(1) = 12$", 1, "HSC"),
        ("$f(x) = x^4 - 3x^2$", "x=2", 20.0, "$f'(x) = 4x^3 - 6x \\Rightarrow f'(2) = 32 - 12 = 20$", 2, "BCS"),
        ("$f(x) = 5x^2 + 3x$", "x=3", 33.0, "$f'(x) = 10x + 3 \\Rightarrow f'(3) = 33$", 1, "HSC"),
        ("$f(x) = \\ln x$", "x=1", 1.0, "$f'(x) = 1/x \\Rightarrow f'(1) = 1$", 2, "admission"),
        ("$f(x) = \\cos x$", "x=0", 0.0, "$f'(x) = -\\sin x \\Rightarrow f'(0) = 0$", 1, "BCS"),
        ("$f(x) = e^{2x}$", "x=0", 2.0, "$f'(x) = 2e^{2x} \\Rightarrow f'(0) = 2$", 2, "HSC"),
        ("$f(x) = x^5$", "x=1", 5.0, "$f'(x) = 5x^4 \\Rightarrow f'(1) = 5$", 1, "admission"),
        ("$f(x) = \\sqrt{x}$", "x=4", 0.25, "$f'(x) = \\frac{1}{2\\sqrt{x}} \\Rightarrow f'(4) = 0.25$", 2, "BCS"),
    ]
    for expr, at, val, expl, diff, tag in configs:
        qs.append(_num(
            f"Find the derivative of {expr} at ${at}$.",
            val,
            expl,
            "Mathematics", "Calculus", "Derivatives", diff, tag,
            tolerance=0.01,
        ))

    # Definite integrals
    int_configs = [
        # (stem, val, expl, diff, tag)
        (r"$\int_0^3 2x\,dx$", 9.0, "$[x^2]_0^3 = 9$", 1, "HSC"),
        (r"$\int_1^4 3x^2\,dx$", 63.0, "$[x^3]_1^4 = 64 - 1 = 63$", 2, "BCS"),
        (r"$\int_0^1 e^x\,dx$", round(2.71828 - 1, 5), "$[e^x]_0^1 = e - 1 \\approx 1.718$", 2, "admission"),
        (r"$\int_0^{\pi/2} \cos x\,dx$", 1.0, "$[\\sin x]_0^{\\pi/2} = 1 - 0 = 1$", 2, "HSC"),
        (r"$\int_1^2 \frac{1}{x}\,dx$", round(__import__('math').log(2), 5),
         "$[\\ln x]_1^2 = \\ln 2 \\approx 0.693$", 3, "BCS"),
        (r"$\int_0^2 (x^2 + 1)\,dx$", round(2**3/3 + 2, 4), "$[x^3/3 + x]_0^2 = 8/3 + 2 \\approx 4.667$", 2, "admission"),
    ]
    for stem, val, expl, diff, tag in int_configs:
        qs.append(_num(
            f"Evaluate {stem}.",
            val,
            expl,
            "Mathematics", "Calculus", "Integrals", diff, tag,
            tolerance=0.01,
        ))

    return qs


def generate_probability_mcq():
    qs = []
    configs = [
        # (n_favourable, n_total, context, tag, diff)
        (1, 6, "rolling a die and getting a 4", "HSC", 1),
        (2, 52, "drawing a king from a standard deck", "BCS", 2),
        (13, 52, "drawing a heart from a standard deck", "HSC", 2),
        (3, 6, "rolling an odd number on a die", "admission", 1),
        (4, 52, "drawing an ace from a standard deck", "BCS", 2),
    ]
    for fav, total, ctx, tag, diff in configs:
        from fractions import Fraction
        f = Fraction(fav, total)
        qs.append(_num(
            f"Find the probability of {ctx}.",
            fav / total,
            f"$P = {fav}/{total} = {float(Fraction(fav, total)):.4f}$",
            "Mathematics", "Statistics", "Probability", diff, tag,
            tolerance=0.001,
        ))
    return qs


def generate_trig_values():
    import math
    qs = []
    configs = [
        # (angle_deg, fn, val, tag, diff)
        (0, "\\sin", 0.0, "HSC", 1),
        (90, "\\sin", 1.0, "HSC", 1),
        (60, "\\cos", 0.5, "BCS", 1),
        (45, "\\tan", 1.0, "admission", 1),
        (30, "\\cos", round(math.cos(math.radians(30)), 4), "HSC", 1),
        (120, "\\sin", round(math.sin(math.radians(120)), 4), "BCS", 2),
        (135, "\\cos", round(math.cos(math.radians(135)), 4), "admission", 2),
        (180, "\\sin", 0.0, "HSC", 1),
        (270, "\\cos", 0.0, "BCS", 1),
        (60, "\\tan", round(math.tan(math.radians(60)), 4), "HSC", 2),
    ]
    for deg, fn, val, tag, diff in configs:
        qs.append(_num(
            f"Find the exact value of ${fn} {deg}°$.",
            float(val),
            f"${fn} {deg}° = {val}$",
            "Mathematics", "Trigonometry", "Identities", diff, tag,
            tolerance=0.001,
        ))
    return qs


def generate_geometry_area_problems():
    qs = []
    import math
    configs = [
        # shape, params, area, explanation, tag, diff
        ("rectangle", "length $10\\,\\text{cm}$, width $4\\,\\text{cm}$", 40.0,
         "$A = l \\times w = 10 \\times 4 = 40\\,\\text{cm}^2$", "HSC", 1),
        ("square", "side $7\\,\\text{cm}$", 49.0,
         "$A = s^2 = 49\\,\\text{cm}^2$", "BCS", 1),
        ("circle", "$r = 5\\,\\text{cm}$", round(math.pi * 25, 4),
         "$A = \\pi r^2 = 25\\pi \\approx 78.54\\,\\text{cm}^2$", "admission", 2),
        ("triangle", "base $8\\,\\text{cm}$, height $6\\,\\text{cm}$", 24.0,
         "$A = \\frac{1}{2} \\times 8 \\times 6 = 24\\,\\text{cm}^2$", "HSC", 1),
        ("trapezoid", "parallel sides $6$ and $10$, height $5$", 40.0,
         "$A = \\frac{1}{2}(6+10)(5) = 40$", "BCS", 2),
        ("circle", "$r = 3\\,\\text{cm}$", round(math.pi * 9, 4),
         "$A = 9\\pi \\approx 28.27\\,\\text{cm}^2$", "HSC", 2),
        ("parallelogram", "base $12$, height $5$", 60.0,
         "$A = bh = 12 \\times 5 = 60$", "admission", 1),
    ]
    for shape, params, area, expl, tag, diff in configs:
        qs.append(_num(
            f"Find the area of a {shape} with {params}.",
            area,
            expl,
            "Mathematics", "Geometry", "Triangles" if shape == "triangle" else "Circles" if shape == "circle" else "Coordinate Geometry",
            diff, tag,
            tolerance=0.1,
        ))
    return qs


# ---------------------------------------------------------------------------
# Assemble all questions
# ---------------------------------------------------------------------------

def generate_optics_extra():
    P, CH = "Physics", "Optics"
    qs = []
    # Reflection extras
    for f, u, tag, diff in [(15, 45, "HSC", 2), (20, 60, "BCS", 3), (10, 40, "admission", 3)]:
        # mirror: 1/v + 1/u = 1/f  (using sign convention: u negative for real object)
        # simplified positive-values formula for concave mirror real object real image
        v = round(f * u / (u - f), 2)
        qs.append(_num(
            f"A concave mirror of focal length $f = {f}\\,\\text{{cm}}$ has an object at "
            f"$u = {u}\\,\\text{{cm}}$. Find image distance $v$ (cm).",
            v,
            f"$\\frac{{1}}{{v}} = \\frac{{1}}{{f}} - \\frac{{1}}{{u}} = \\frac{{1}}{{{f}}} - \\frac{{1}}{{{u}}} \\Rightarrow v = {v}\\,\\text{{cm}}$",
            P, CH, "Reflection", diff, tag, tolerance=0.2,
        ))
    # Refraction extras
    for n, theta_i, tag, diff in [(1.5, 45, "HSC", 2), (1.33, 30, "BCS", 2), (1.6, 60, "admission", 3)]:
        import math
        theta_r = round(math.degrees(math.asin(math.sin(math.radians(theta_i)) / n)), 1)
        qs.append(_num(
            f"Light enters a medium with $n = {n}$ from air at $\\theta_i = {theta_i}°$. "
            f"Find angle of refraction (degrees, 1 dp).",
            theta_r,
            f"$\\sin\\theta_r = \\sin {theta_i}° / {n} \\Rightarrow \\theta_r \\approx {theta_r}°$",
            P, CH, "Refraction", diff, tag, tolerance=0.2,
        ))
    # Wave optics extras
    for lam, D, d, tag, diff in [(500e-9, 1.0, 0.5e-3, "HSC", 3), (600e-9, 1.5, 1e-3, "BCS", 3)]:
        beta = round(lam * D / d * 1000, 4)  # in mm
        qs.append(_num(
            f"In YDSE, $\\lambda = {int(lam*1e9)}\\,\\text{{nm}}$, $D = {D}\\,\\text{{m}}$, "
            f"$d = {d*1e3}\\,\\text{{mm}}$. Fringe width (in mm):",
            beta,
            f"$\\beta = \\lambda D/d = {lam} \\times {D} / {d} = {beta}\\,\\text{{mm}}$",
            P, CH, "Wave Optics", diff, tag, tolerance=0.05,
        ))
    # TIR critical angle problems
    for n, tag, diff in [(1.5, "HSC", 2), (1.33, "BCS", 2), (2.0, "admission", 3)]:
        import math
        theta_c = round(math.degrees(math.asin(1/n)), 1)
        qs.append(_num(
            f"Find the critical angle (degrees, 1 dp) for a medium with $n = {n}$ in contact with air.",
            theta_c,
            f"$\\theta_c = \\sin^{{-1}}(1/{n}) \\approx {theta_c}°$",
            P, CH, "Refraction", diff, tag, tolerance=0.2,
        ))
    # Magnification
    for f_cm, u_cm, tag, diff in [(10, 30, "HSC", 2), (15, 45, "BCS", 2), (20, 80, "admission", 3)]:
        v = f_cm * u_cm / (u_cm - f_cm)
        m = round(-v / u_cm, 3)
        qs.append(_num(
            f"Concave mirror $f = {f_cm}\\,\\text{{cm}}$, object at $u = {u_cm}\\,\\text{{cm}}$. "
            f"Magnification $m$ (negative = inverted):",
            m,
            f"$v = {round(v,2)}\\,\\text{{cm}}$, $m = -v/u = {m}$",
            P, CH, "Reflection", diff, tag, tolerance=0.05,
        ))
    return qs


def generate_modern_physics_extra():
    P, CH = "Physics", "Modern Physics"
    qs = []
    h = 6.626e-34
    c = 3e8
    # Photon energy problems
    for freq_THz, tag, diff in [(500, "HSC", 2), (750, "BCS", 2), (300, "admission", 2)]:
        f = freq_THz * 1e12
        E = round(h * f / 1.6e-19, 4)  # in eV
        qs.append(_num(
            f"Find the energy (in eV) of a photon with frequency $f = {freq_THz}\\,\\text{{THz}}$. "
            f"Use $h = 6.626 \\times 10^{{-34}}\\,\\text{{J·s}}$.",
            E,
            f"$E = hf = 6.626\\times10^{{-34}} \\times {f:.2e}\\,\\text{{J}} = {E}\\,\\text{{eV}}$",
            P, CH, "Photoelectric Effect", diff, tag, tolerance=0.05,
        ))
    # Bohr orbit radius
    a0 = 0.529  # Angstrom
    for n, tag, diff in [(2, "HSC", 2), (3, "BCS", 2), (4, "admission", 3)]:
        r = round(a0 * n**2, 3)
        qs.append(_num(
            f"Find the radius of the $n = {n}$ Bohr orbit of hydrogen in Angstroms. "
            f"($a_0 = 0.529\\,\\text{{Å}}$)",
            r,
            f"$r_n = a_0 n^2 = 0.529 \\times {n}^2 = {r}\\,\\text{{Å}}$",
            P, CH, "Atomic Models", diff, tag, tolerance=0.01,
        ))
    # Hydrogen energy levels
    for n, tag, diff in [(3, "HSC", 2), (4, "BCS", 2), (5, "admission", 3)]:
        E = round(-13.6 / n**2, 4)
        qs.append(_num(
            f"Find the energy (eV) of the $n = {n}$ level of hydrogen.",
            E,
            f"$E_n = -13.6/n^2 = -13.6/{n}^2 = {E}\\,\\text{{eV}}$",
            P, CH, "Atomic Models", diff, tag, tolerance=0.01,
        ))
    # Half-life problems
    for t12, periods, tag, diff in [(10, 2, "HSC", 1), (6, 4, "BCS", 2), (8, 3, "admission", 2)]:
        t = t12 * periods
        frac = round((0.5)**periods, 6)
        qs.append(_num(
            f"Radioactive sample has half-life $T_{{1/2}} = {t12}\\,\\text{{days}}$. "
            f"Fraction remaining after ${t}\\,\\text{{days}}$:",
            frac,
            f"{periods} half-lives → $(1/2)^{{{periods}}} = {frac}$",
            P, CH, "Nuclear Physics", diff, tag, tolerance=0.001,
        ))
    # de Broglie wavelength
    for m_kg, v_ms, tag, diff in [(9.1e-31, 1e6, "BCS", 3), (1.67e-27, 1e4, "admission", 3)]:
        lam = round(h / (m_kg * v_ms), 15)
        qs.append(_num(
            f"Find de Broglie wavelength (m) for a particle of mass $m = {m_kg:.2e}\\,\\text{{kg}}$ "
            f"moving at $v = {v_ms:.0e}\\,\\text{{m/s}}$.",
            lam,
            f"$\\lambda = h/(mv) = 6.626\\times10^{{-34}} / ({m_kg:.2e} \\times {v_ms:.0e}) = {lam:.3e}\\,\\text{{m}}$",
            P, CH, "Atomic Models", diff, tag, tolerance=lam * 0.05,
        ))
    return qs


def generate_thermo_extra():
    P, CH = "Physics", "Thermodynamics"
    qs = []
    R = 8.314  # J/(mol·K)
    # Ideal gas work done
    for P_atm, V1, V2, tag, diff in [
        (2, 1, 3, "HSC", 2), (1, 2, 5, "BCS", 2), (3, 1, 4, "admission", 3)
    ]:
        W = round(P_atm * 101325 * (V2 - V1) * 1e-3, 1)  # Pa × m³
        qs.append(_num(
            f"An ideal gas expands isobarically at $P = {P_atm}\\,\\text{{atm}}$ "
            f"from $V_1 = {V1}\\,\\text{{L}}$ to $V_2 = {V2}\\,\\text{{L}}$. Work done (J):",
            W,
            f"$W = P\\Delta V = {P_atm} \\times 101325 \\times {(V2-V1)/1000}\\,\\text{{m}}^3 = {W}\\,\\text{{J}}$",
            P, CH, "Laws of Thermodynamics", diff, tag, tolerance=abs(W)*0.05,
        ))
    # Carnot efficiency problems
    for T_H, T_C, tag, diff in [
        (600, 300, "HSC", 2), (800, 400, "BCS", 2), (1000, 200, "admission", 3)
    ]:
        eta = round(1 - T_C / T_H, 4)
        qs.append(_num(
            f"Carnot engine between $T_H = {T_H}\\,\\text{{K}}$ and $T_C = {T_C}\\,\\text{{K}}$. "
            f"Efficiency (as decimal fraction):",
            eta,
            f"$\\eta = 1 - T_C/T_H = 1 - {T_C}/{T_H} = {eta}$",
            P, CH, "Laws of Thermodynamics", diff, tag, tolerance=0.001,
        ))
    # Charles' law problems
    for T1, V1, T2, tag, diff in [
        (300, 2, 600, "HSC", 1), (273, 1, 546, "BCS", 1), (400, 3, 800, "admission", 2)
    ]:
        V2 = round(V1 * T2 / T1, 2)
        qs.append(_num(
            f"Gas at $T_1 = {T1}\\,\\text{{K}}$, $V_1 = {V1}\\,\\text{{L}}$. At $T_2 = {T2}\\,\\text{{K}}$ "
            f"(pressure constant), find $V_2$ (L):",
            V2,
            f"$V_2 = V_1 T_2/T_1 = {V1} \\times {T2}/{T1} = {V2}\\,\\text{{L}}$",
            P, CH, "Ideal Gas", diff, tag, tolerance=0.05,
        ))
    # Specific heat
    for m, c_sp, dT, tag, diff in [
        (2, 4186, 10, "HSC", 1), (0.5, 900, 50, "BCS", 2), (3, 450, 20, "admission", 2)
    ]:
        Q = m * c_sp * dT
        qs.append(_num(
            f"Find heat required (J) to raise $m = {m}\\,\\text{{kg}}$ by $\\Delta T = {dT}\\,\\text{{K}}$. "
            f"Specific heat $c = {c_sp}\\,\\text{{J/(kg·K)}}$.",
            float(Q),
            f"$Q = mc\\Delta T = {m} \\times {c_sp} \\times {dT} = {Q}\\,\\text{{J}}$",
            P, CH, "Heat Transfer", diff, tag, tolerance=float(Q)*0.01,
        ))
    return qs


def generate_multi_mcq():
    """Multi-select questions across subjects."""
    def mmcq(stem, options, correct_ids, explanation, subject, chapter, topic, difficulty, exam_tag):
        return {
            "type": "multi_mcq",
            "subject": subject, "chapter": chapter, "topic": topic,
            "difficulty": difficulty, "exam_tag": exam_tag,
            "stem": stem,
            "options": options,
            "correct": {"ids": correct_ids},
            "explanation": explanation,
            "language": "en",
        }

    qs = [
        mmcq(
            "Which of the following are vector quantities? (Select ALL that apply.)",
            opts("a", "Velocity", "b", "Speed", "c", "Displacement", "d", "Distance", "e", "Force"),
            ["a", "c", "e"],
            "Vectors have both magnitude and direction: velocity, displacement, force. Speed and distance are scalars.",
            "Physics", "Mechanics", "Kinematics", 2, "HSC",
        ),
        mmcq(
            "Which statements about Newton's laws are correct? (Select ALL that apply.)",
            opts(
                "a", "An object at rest stays at rest unless acted on by a net force",
                "b", "$F = ma$ (net force = mass × acceleration)",
                "c", "Action and reaction act on the same body",
                "d", "Every action has an equal and opposite reaction",
            ),
            ["a", "b", "d"],
            "Newton's 3rd law: action/reaction on *different* bodies, not the same body.",
            "Physics", "Mechanics", "Dynamics", 2, "BCS",
        ),
        mmcq(
            "Which forms of energy are conserved in a perfectly elastic collision?",
            opts("a", "Kinetic energy", "b", "Momentum", "c", "Potential energy", "d", "Total mechanical energy"),
            ["a", "b"],
            "Elastic collision: KE and momentum both conserved. PE and total ME are not generally conserved unless there are no external fields.",
            "Physics", "Mechanics", "Momentum", 3, "admission",
        ),
        mmcq(
            "Which of the following are properties of electric field lines?",
            opts(
                "a", "They originate from positive charges",
                "b", "They can intersect at right angles",
                "c", "They terminate at negative charges",
                "d", "Their density indicates field strength",
            ),
            ["a", "c", "d"],
            "Field lines: +→−, never intersect, density ∝ field strength.",
            "Physics", "Electromagnetism", "Electrostatics", 2, "HSC",
        ),
        mmcq(
            "Which of the following can undergo total internal reflection?",
            opts(
                "a", "Light going from glass to air",
                "b", "Light going from air to glass",
                "c", "Light going from water to air",
                "d", "Light going from diamond to air",
            ),
            ["a", "c", "d"],
            "TIR occurs only going from denser to rarer medium (glass/water/diamond → air).",
            "Physics", "Optics", "Refraction", 2, "BCS",
        ),
        mmcq(
            "Which of the following are correct thermodynamic statements?",
            opts(
                "a", "In an adiabatic process, $Q = 0$",
                "b", "Entropy of an isolated system always decreases",
                "c", "In an isothermal process, $\\Delta U = 0$ for an ideal gas",
                "d", "The Carnot engine has the maximum possible efficiency between two temperatures",
            ),
            ["a", "c", "d"],
            "Entropy always *increases* (or stays constant) in isolated systems — second law.",
            "Physics", "Thermodynamics", "Laws of Thermodynamics", 3, "admission",
        ),
        mmcq(
            "Which of the following are true for a quadratic $ax^2 + bx + c = 0$ with $\\Delta > 0$?",
            opts(
                "a", "It has two distinct real roots",
                "b", "The roots are complex",
                "c", "Sum of roots $= -b/a$",
                "d", "Product of roots $= c/a$",
            ),
            ["a", "c", "d"],
            "$\\Delta > 0$: two distinct real roots. Sum $= -b/a$, product $= c/a$ (Vieta).",
            "Mathematics", "Algebra", "Quadratics", 2, "HSC",
        ),
        mmcq(
            "Which of the following integrals equal 0?",
            opts(
                "a", r"$\int_{-\pi}^{\pi} \sin x\,dx$",
                "b", r"$\int_{-1}^{1} x^3\,dx$",
                "c", r"$\int_{0}^{1} x^2\,dx$",
                "d", r"$\int_{-2}^{2} x\,dx$",
            ),
            ["a", "b", "d"],
            "Odd functions ($\\sin x$, $x^3$, $x$) integrate to 0 over symmetric intervals.",
            "Mathematics", "Calculus", "Integrals", 3, "BCS",
        ),
        mmcq(
            "Which are measures of central tendency?",
            opts("a", "Mean", "b", "Median", "c", "Variance", "d", "Mode", "e", "Standard deviation"),
            ["a", "b", "d"],
            "Central tendency: mean, median, mode. Variance and SD are measures of spread.",
            "Mathematics", "Statistics", "Descriptive Statistics", 1, "HSC",
        ),
        mmcq(
            "Which of the following are Pythagorean trigonometric identities?",
            opts(
                "a", "$\\sin^2\\theta + \\cos^2\\theta = 1$",
                "b", "$1 + \\tan^2\\theta = \\sec^2\\theta$",
                "c", "$\\sin\\theta + \\cos\\theta = 1$",
                "d", "$1 + \\cot^2\\theta = \\csc^2\\theta$",
            ),
            ["a", "b", "d"],
            "Three Pythagorean identities: divide $\\sin^2+\\cos^2=1$ by $\\cos^2$ or $\\sin^2$.",
            "Mathematics", "Trigonometry", "Identities", 2, "admission",
        ),
        mmcq(
            "Which statements about probability are correct?",
            opts(
                "a", "For any event $A$: $0 \\leq P(A) \\leq 1$",
                "b", "$P(A \\cup B) = P(A) + P(B)$ always",
                "c", "$P(A) + P(A^c) = 1$",
                "d", "For independent $A$, $B$: $P(A \\cap B) = P(A)P(B)$",
            ),
            ["a", "c", "d"],
            "$P(A \\cup B) = P(A) + P(B) - P(A \\cap B)$ — not simply a sum unless mutually exclusive.",
            "Mathematics", "Statistics", "Probability", 2, "BCS",
        ),
        mmcq(
            "Which of the following always hold for any triangle $ABC$?",
            opts(
                "a", "$A + B + C = 180°$",
                "b", "$a^2 = b^2 + c^2$ (Pythagoras)",
                "c", "$\\frac{a}{\\sin A} = \\frac{b}{\\sin B}$ (sine rule)",
                "d", "$c^2 = a^2 + b^2 - 2ab\\cos C$ (cosine rule)",
            ),
            ["a", "c", "d"],
            "Pythagorean theorem holds only for right triangles. Angle sum, sine rule, cosine rule are universal.",
            "Mathematics", "Trigonometry", "Applications", 3, "HSC",
        ),
        mmcq(
            "Which of the following are properties of the determinant?",
            opts(
                "a", "$\\det(AB) = \\det(A)\\det(B)$",
                "b", "$\\det(A^T) = \\det(A)$",
                "c", "$\\det(2A) = 2\\det(A)$ for a $2\\times 2$ matrix",
                "d", "Swapping two rows negates the determinant",
            ),
            ["a", "b", "d"],
            "$\\det(2A) = 2^n \\det(A)$ for $n \\times n$ — for $2\\times 2$ it's $4\\det(A)$, not $2\\det(A)$.",
            "Mathematics", "Algebra", "Matrices", 3, "admission",
        ),
        mmcq(
            "Which of the following radioactive decay modes conserve mass number $A$?",
            opts(
                "a", "Alpha decay",
                "b", "Beta-minus decay",
                "c", "Gamma decay",
                "d", "All conserve $A$",
            ),
            ["b", "c"],
            "Alpha decay: $A$ decreases by 4. Beta and gamma: $A$ unchanged. So NOT all conserve $A$.",
            "Physics", "Modern Physics", "Nuclear Physics", 3, "BCS",
        ),
        mmcq(
            "For a function $f(x)$ to have a local minimum at $x = a$, which conditions are sufficient?",
            opts(
                "a", "$f'(a) = 0$",
                "b", "$f''(a) > 0$",
                "c", "$f''(a) < 0$",
                "d", "$f'$ changes from negative to positive at $a$",
            ),
            ["a", "b", "d"],
            "Local min: $f'=0$ and $f''>0$ (second derivative test), OR $f'$ changes $-→+$ (first derivative test).",
            "Mathematics", "Calculus", "Applications of Calculus", 3, "HSC",
        ),
    ]
    return qs


def generate_all_questions():
    qs = []
    qs.extend(physics_mechanics())
    qs.extend(physics_thermo())
    qs.extend(physics_em())
    qs.extend(physics_optics())
    qs.extend(physics_modern())
    qs.extend(math_algebra())
    qs.extend(math_calculus())
    qs.extend(math_geometry())
    qs.extend(math_stats())
    qs.extend(math_trig())
    # Programmatic fill-up
    qs.extend(generate_kinematics_numericals())
    qs.extend(generate_circuit_numericals())
    qs.extend(generate_algebra_numericals())
    qs.extend(generate_calculus_numericals())
    qs.extend(generate_probability_mcq())
    qs.extend(generate_trig_values())
    qs.extend(generate_geometry_area_problems())
    # Boost thin chapters
    qs.extend(generate_optics_extra())
    qs.extend(generate_modern_physics_extra())
    qs.extend(generate_thermo_extra())
    # Multi-select questions (covers all types: single_mcq, multi_mcq, true_false, numerical now present)
    qs.extend(generate_multi_mcq())
    # Final batch to reach ~300
    qs.extend([
        _num("Find $\\log_{10} 1000$.", 3.0, "$10^3 = 1000$", "Mathematics", "Algebra", "Polynomials", 1, "HSC"),
        _num("Find $\\log_2 64$.", 6.0, "$2^6 = 64$", "Mathematics", "Algebra", "Polynomials", 1, "BCS"),
        _tf("$\\log(AB) = \\log A + \\log B$ for positive $A$, $B$.", True, "Product rule of logarithms.", "Mathematics", "Algebra", "Polynomials", 1, "HSC"),
        _mcq("$\\frac{d}{dx}(\\ln x) = $", opts("a", "$1/x$", "b", "$x$", "c", "$\\ln x$", "d", "$e^x$"), "a", "$\\frac{d}{dx}\\ln x = 1/x$", "Mathematics", "Calculus", "Derivatives", 1, "admission"),
        _num("Find the perimeter of a rectangle: length $12\\,\\text{cm}$, width $5\\,\\text{cm}$.", 34.0, "$P = 2(l+w) = 2(17) = 34\\,\\text{cm}$", "Mathematics", "Geometry", "Coordinate Geometry", 1, "HSC"),
        _tf("The median divides a triangle into two triangles of equal area.", True, "Each sub-triangle has same base (half of original) and same height — equal areas.", "Mathematics", "Geometry", "Triangles", 2, "BCS"),
        _mcq("$\\sin 90° = $", opts("a", "0", "b", "1", "c", "$\\sqrt{2}/2$", "d", "undefined"), "b", "$\\sin 90° = 1$", "Mathematics", "Trigonometry", "Identities", 1, "HSC"),
        _num("A sample has values $\\{1, 2, 3, 4, 5\\}$. Find the range.", 4.0, "Range $= \\max - \\min = 5 - 1 = 4$", "Mathematics", "Statistics", "Descriptive Statistics", 1, "BCS"),
        _mcq("The work done by gravity when an object of mass $m$ falls height $h$ is:", opts("a", "$-mgh$", "b", "$mgh$", "c", "$mgh^2$", "d", "0"), "b", "Gravity does positive work when displacement is in direction of force.", "Physics", "Mechanics", "Energy", 1, "HSC"),
        _tf("Sound waves are transverse waves.", False, "Sound waves are longitudinal (compression waves). Light and water surface waves are transverse.", "Physics", "Mechanics", "Kinematics", 2, "BCS"),
        _mcq("The unit of electric charge is:", opts("a", "Volt", "b", "Ampere", "c", "Coulomb", "d", "Farad"), "c", "SI unit of charge: Coulomb (C). $1\\,\\text{C} = 1\\,\\text{A·s}$.", "Physics", "Electromagnetism", "Electrostatics", 1, "HSC"),
        _mcq("Absolute zero temperature in Celsius is:", opts("a", "$0°\\text{C}$", "b", "$-100°\\text{C}$", "c", "$-273.15°\\text{C}$", "d", "$-373°\\text{C}$"), "c", "$0\\,\\text{K} = -273.15°\\text{C}$", "Physics", "Thermodynamics", "Ideal Gas", 1, "admission"),
        _tf("The speed of light in vacuum is approximately $3 \\times 10^8\\,\\text{m/s}$.", True, "Exact value: $c = 299{,}792{,}458\\,\\text{m/s} \\approx 3 \\times 10^8\\,\\text{m/s}$.", "Physics", "Modern Physics", "Photoelectric Effect", 1, "HSC"),
    ])
    return qs


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 1,
    type TEXT NOT NULL,
    subject TEXT NOT NULL,
    chapter TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL,
    exam_tag TEXT NOT NULL,
    stem TEXT NOT NULL,
    options JSONB,
    correct JSONB NOT NULL,
    explanation TEXT,
    media JSONB,
    language TEXT NOT NULL DEFAULT 'en',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_questions_taxonomy
    ON questions (subject, chapter, topic, difficulty, exam_tag);

CREATE TABLE IF NOT EXISTS tests (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    question_ids JSONB NOT NULL,
    filters JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS attempts (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    test_id UUID,
    question_id UUID NOT NULL,
    question_version INTEGER NOT NULL,
    selected JSONB NOT NULL,
    is_correct BOOLEAN,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    scored_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_stats (
    user_id TEXT PRIMARY KEY,
    total_attempted INTEGER NOT NULL DEFAULT 0,
    total_correct INTEGER NOT NULL DEFAULT 0,
    accuracy_by_topic JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

INSERT_QUESTION_SQL = """
INSERT INTO questions
    (id, version, type, subject, chapter, topic, difficulty, exam_tag,
     stem, options, correct, explanation, media, language, is_active)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
ON CONFLICT (id) DO NOTHING
"""


async def main():
    url = DATABASE_URL
    print(f"Connecting to: {url}")
    conn = await asyncpg.connect(url)

    print("Creating tables...")
    await conn.execute(CREATE_TABLES_SQL)

    questions = generate_all_questions()
    print(f"Inserting {len(questions)} questions...")

    inserted = 0
    for q in questions:
        qid = uuid.uuid4()
        await conn.execute(
            INSERT_QUESTION_SQL,
            qid,
            1,                              # version
            q["type"],
            q["subject"],
            q["chapter"],
            q["topic"],
            q["difficulty"],
            q["exam_tag"],
            q["stem"],
            json.dumps(q["options"]) if q.get("options") is not None else None,
            json.dumps(q["correct"]),
            q.get("explanation"),
            json.dumps(q.get("media")) if q.get("media") else None,
            q.get("language", "en"),
            True,
        )
        inserted += 1

    await conn.close()

    print(f"Done. {inserted} questions inserted.")
    print("\nBreakdown by subject/chapter:")
    from collections import Counter
    counts = Counter((q["subject"], q["chapter"]) for q in questions)
    for (subj, chap), n in sorted(counts.items()):
        print(f"  {subj} / {chap}: {n}")
    print(f"\nTotal: {len(questions)}")


if __name__ == "__main__":
    asyncio.run(main())
