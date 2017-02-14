# The problem:
You need to perform multiple computational simulations covering a parameter space.

# The solution:
**Chauffeur** is a simple Python solution to generate and execute multiple simulations driven by intuitive YAML-based configurations.

**Chauffeur** supports parameterization at all levels of the driver process. Autogenerate directories and input files, dynamically select executables, and perform pre- and post-execution tasks.

# Requirements
- Python 3.4+
- [PyYAML](http://pyyaml.org/)

# Examples

## Multiple sequential runs in one directory
```yaml
driver:
    rundir: "./"
    executable: "a.exe"
    templatefile: "input_template"
    paramfile: "%(rundir)/input"

run1:
  variableorder: [a,b]
  variables:
    b: [1,2]
    a: [4,5]
  parameters:
    c: 1.0
```