import numpy as np
import pytest
import sympy as sp

from experiments import numeric, symbolic
def _allclose(a, b, atol=1e-10, rtol=1e-10):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return np.allclose(a, b, atol=atol, rtol=rtol)
def test_exp1_symbolic_closed_form_matches_summation():
    r, n = sp.symbols("r n")
    k = sp.Symbol("k", integer=True)
    summ = sp.summation(r**k, (k, 0, n - 1))
    deriv = symbolic.exp1_geometric_series()
    assert sp.simplify(summ - deriv.final) == 0
def test_exp2_symbolic_solution_satisfies_ode_and_ic():
    t, a, b, x0, x_expr = symbolic.exp2_closed_form_symbols()
    xt = sp.simplify(x_expr.subs(t, 0))
    assert sp.simplify(xt - x0) == 0
    ode_residual = sp.simplify(sp.diff(x_expr, t) - (a * x_expr + b))
    assert sp.simplify(ode_residual) == 0
def test_exp3_symbolic_posterior_equivalences():
    mu0, s0, s, n, xbar, mat = symbolic.exp3_closed_form_symbols()
    mean_wa, post_var = map(sp.simplify, list(mat))
    prec0 = 1 / s0**2
    prec = n / s**2
    mean_prec = sp.simplify((prec0 * mu0 + prec * xbar) / (prec0 + prec))
    var_prec = sp.simplify(1 / (prec0 + prec))
    assert sp.simplify(mean_wa - mean_prec) == 0
    assert sp.simplify(post_var - var_prec) == 0
@pytest.mark.parametrize("seed", [0, 1])
def test_numeric_matches_symbolic_randomized(seed):
    rng = np.random.default_rng(seed)

    r = rng.uniform(0.5, 1.5, size=500)
    n = rng.integers(1, 60, size=500)
    r_sym, n_sym, e1 = symbolic.exp1_closed_form_symbols()
    f1 = symbolic.lambdify_expr(e1, (r_sym, n_sym))
    assert _allclose(numeric.exp1_geometric_sum(r, n), f1(r, n), atol=1e-10, rtol=1e-10)

    t = rng.uniform(0.0, 3.0, size=500)
    a = rng.uniform(-1e-8, 1e-8, size=500)
    b = rng.normal(size=500)
    x0 = rng.normal(size=500)
    t_sym, a_sym, b_sym, x0_sym, e2 = symbolic.exp2_closed_form_symbols()
    f2 = symbolic.lambdify_expr(e2, (t_sym, a_sym, b_sym, x0_sym))
    assert _allclose(numeric.exp2_affine_ode(t, a, b, x0), f2(t, a, b, x0), atol=1e-8, rtol=1e-8)

    mu0 = rng.normal(size=500)
    s0 = rng.uniform(0.2, 3.0, size=500)
    s = rng.uniform(0.2, 3.0, size=500)
    nn = rng.integers(1, 200, size=500)
    xbar = rng.normal(size=500)
    mu0_s, s0_s, s_s, n_s, xbar_s, e3 = symbolic.exp3_closed_form_symbols()
    f3 = symbolic.lambdify_expr(e3, (mu0_s, s0_s, s_s, n_s, xbar_s))
    mean, var = numeric.exp3_normal_normal(mu0, s0, s, nn, xbar)
    sym = np.asarray(f3(mu0, s0, s, nn, xbar), dtype=float)
    assert _allclose(mean, sym[0])
    assert _allclose(var, sym[1])
def test_numeric_edge_cases_no_nan_and_exact_limits():
    # exp1: r==1 => S==n
    assert float(numeric.exp1_geometric_sum(1.0, 7)) == 7.0
    assert np.all(np.isfinite(numeric.exp1_geometric_sum(np.array([1.0, 1.0]), np.array([3, 9]))))

    # exp2: a==0 => x0 + b t (exact branch)
    t = np.array([0.0, 0.5, 2.0])
    out = numeric.exp2_affine_ode(t, 0.0, 3.0, -1.0)
    assert _allclose(out, -1.0 + 3.0 * t, atol=0.0, rtol=0.0)
def test_reference_check_regression_tolerances():
    # quick end-to-end consistency gate
    res = numeric.reference_check(seed=123, atol=1e-10, rtol=1e-10)
    assert res == {"exp1": True, "exp2": True, "exp3": True}
