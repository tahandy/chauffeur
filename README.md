# The problem:
You need to perform multiple computational simulations covering a parameter space.

# The solution:
**Chauffeur** is a simple Python solution to generate and execute multiple simulations driven by intuitive YAML-based configurations.

**Chauffeur** supports parameterization at all levels of the driver process. Autogenerate directories and input files, dynamically select executables, and perform pre-and post-execution tasks.

---
# Requirements
- Python 3.4+
- [PyYAML](http://pyyaml.org/)

---
# Usage
```
chauffeur.py [-h] [-i INPUT]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        specify input YAML file
```

---

# Execution flow

In the most general case, **chauffeur** will attempt to perform the following actions:

- For each run defined by the tensor product of variables:
  - Copy a template directory to the execution/run directory
  - Process parameterized files
  - Perform pre-execution command
  - Perform execution command
  - Perform post-execution command

Execution of individual runs can be performed in serial, or in parallel across
threads. Note this does not imply anything about the parallelization of the
underlying executable; your executable command may invoke something like MPI
to further parallelize the run. For example, you may execute 3 runs in
task-wise parallel, each using a number of MPI cores.

Additionally, **chauffeur** may be used to setup the directory structures and
generate submission files for job management systems like PBS/Torque.

---
# Parameterization

**Chauffeur** operates by parameterizing most aspects of the automation process. Accessing defined parameters is obtained by enclosing the parameter name in '%(...)'. For example, if `var1` is defined (see below), access to this parameter is achieved by using `%(var1)`.

**Chauffeur** supports the use of inline formatting to specify the output format of an evaluated parameter. This inline formatting is based on the equivalent formats for Python 3's `format` statement. For example, if `var1` is an integer, we can format it to print as a width=4 integer with leading zeros using `%(var1:04d)`, where the `:` denotes the beginning of inline formatting and `04d` is the format specifier.

# YAML input structure

The input file that drives **chauffeur** uses the YAML format and is divided into multiple (potentially optional) sections: *driver*, *userdef*, *file\**, and *run\**.

- *driver* specifies executables, threads, etc.
- *userdef* specifies user-defined parameters for convenience (optional)
- *file\** sections define text files which should undergo parameter replacement (optional)
- *run\** sections define the parameter space

## Driver
The driver section is specified by the top-level identifier `driver:`. The available options are:

Modifiable parameters:
`rundir     `                  = '%(cwd)'
`templatedir`                       = None
`type       `                = 'exec'
`dryrun     `                  = True
`skipifexist`                       = True
`nthreads   `                     = 1



Fix parameters:
`cwd        `               = os.getcwd()
`scriptdir  `                     = os.path.realpath(__file__)
`rundir     `                  = '%(cwd)'
`templatedir`                       = None
`type       `                = 'exec'
`dryrun     `                  = True
`skipifexist`                       = True
`nthreads   `                     = 1

  driverData['precommand']    = None
  driverData['execcommand']   = None
  driverData['postcommand']   = None

  # PBS stuff
  driverData['pbs_submitscript'] = '%(cwd)/pbs_submit.sh'
  driverData['pbs_subcommand']   = 'qsub'


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
    execcommand: "mpirun -np %(nproc:%d) %(executable) > runlog"

userdef:
  basedir: "/tmp/mybasedir"

run1:
  variableorder: [a,b]
  variables:
    b: [1,2]
    a: [1.569,3.14]
  parameters:
    c: "superbee"
    nproc: 7

run2:
  variableorder: [a,b]
  variables:
    b: [1,2,3,4]
    a: [0.5, 0.75, 1.0, 2.221]
  parameters:
    c: "minmod"
    nproc: 24
```
