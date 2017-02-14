# The problem:
You need to perform multiple computational simulations covering a parameter space.

# The solution:
**Chauffeur** is a simple Python solution to generate and execute multiple simulations driven by intuitive YAML-based configurations.

**Chauffeur** supports parameterization at all levels of the driver process. Autogenerate directories and input files, dynamically select executables, and perform pre- and post-execution tasks.

# Requirements
- Python 3.4+
- [PyYAML](http://pyyaml.org/)

# Examples

## Parameter file
> ... static input ...
> thisisvarA = %(a)
> thisisvarB = %(b)
> thisisparamC = %(c)
> ... static input ...

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

## Multiple MPI runs simultaneously
```yaml
driver:
    rundir: "%(basedir)/%(thread)"
    templatedir: "%(basedir)/template"
    executable: "a.exe"
    templatefile: "%(templatedir)/input_template"
    paramfile: "%(rundir)/input"
    execcommand: "mpirun -np 2 %(executable) > runlog"

usedef:
  basedir: "/tmp/mybasedir"

run1:
  variableorder: [a,b]
  variables:
    b: [1,2]
    a: [4,5]
  parameters:
    c: 1.0
```

## Multiple MPI runs simultaneously with parameter-based run directories and custom formatting
```yaml
driver:
    rundir: "%(basedir)/vara_%(a:%02d)_varb_%(b:%4e)"
    templatedir: "%(basedir)/template"
    executable: "a.exe"
    templatefile: "%(templatedir)/input_template_%(c)"
    paramfile: "%(rundir)/input"
    execcommand: "mpirun -np 2 %(executable) > runlog"

userdef:
  basedir: "/tmp/mybasedir"

run1:
  variableorder: [a,b]
  variables:
    b: [1,2]
    a: [1.569,3.14]
  parameters:
    c: "superbee"
```
