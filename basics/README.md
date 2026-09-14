# 1D diffusion basics

`diffusion_1d.py` implements the constant-diffusivity problem specified in the
solver PDFs:

\[
\frac{\partial c}{\partial t}=D\frac{\partial^2c}{\partial x^2},
\qquad D=2\;\mathrm{m^2/s},
\]

using Forward Euler in time, central differences in space, and reflected ghost
nodes for zero-gradient boundaries.

Run from the repository root with:

```text
python basics/diffusion_1d.py
```

This writes solution CSV files and initial comparison plots below `results/`.
