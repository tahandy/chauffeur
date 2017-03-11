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

Additionally, **chauffeur** may be used to setup the directory structures and generate submission files for job management systems like PBS/Torque.

---
# Parameterization

**Chauffeur** operates by parameterizing most aspects of the automation process. Accessing defined parameters is obtained by enclosing the parameter name in '%(...)'. For example, if `var1` is defined (see below), access to this parameter is achieved by using `%(var1)`.

## YAML input structure

The input file that drives **chauffeur** uses the YAML format and is divided into multiple (potentially optional) sections: *driver*, *userdef*, *file\**, and *run\**.

- *driver* specifies executables, threads, etc.
- *userdef* specifies user-defined parameters for convenience (optional)
- *file\** sections define text files which should undergo parameter replacement (optional)
- *run\** sections define the parameter space

## Inline formatting
**Chauffeur** supports the use of inline formatting to specify the output format of an evaluated parameter. This inline formatting is based on the equivalent formats for Python 3's `format` statement. For example, if `var1` is an integer, we can format it to print as a width=4 integer with leading zeros using `%(var1:04d)`, where the `:` denotes the beginning of inline formatting and `04d` is the format specifier.

## Expressions
**Chauffeur** includes support for expressions, which are custom combinations of (primarily) numeric parameters. Expressions are enclosed in backticks (\`) and are recursively fed to ```eval```. Parameters including expressions must be enclosed in double quotes (").

> num: 7<br />
> squared: "\`pow(%(num),2)\`"

## Example
A simple input file which echoes parameters is:
```
driver:
  execcommand: "echo %(num) %(times10) %(squared)"
userdef:
  times10: "\`%(num)*10\`"
run:
  variables:
    num: [1,2,3,10,11,37,72]
  parameters:
    squared: "\`pow(%(num),2)\`"
```

---
## Driver
The ```driver``` directive is used to provide overarching parameters to *chauffeur*.

### Modifiable parameters:

**precommand**<br />
Default: ```None```<br />
Description: Set the command to be executed prior to ```execcommand```. Will be executed in ```taskdir```.

**execcommand**<br />
Default: ```None```<br />
Description: Set the command to be executed. Will be executed in ```taskdir```.

**postcommand**<br />
Default: ```None```<br />
Description: Set the command to be executed after ```execcommand```. Will be executed in ```taskdir```.

**taskdir**<br />
Default: ```%(cwd)```<br />
Description: Set the directory a task is executed in. If not task-level parameterized, will reuse the same directory for each task (be careful if threads are used). Default is the directory chauffeur is called from.

**templatedir**<br />
Default: ```None```<br />
Description: Set the directory used to initialize task directories.

**type**<br />
Default: ```exec```<br />
Options: ```exec```, ```setup```<br />
Description: Determines how chauffeur is executed. ```exec``` performs all operations, including running **execcommand**. ```setup``` only initializes run directories, and also produces PBS submission script.

**skipifexist**<br />
Default: ```True```<br />
Options: ```True```, ```False```<br />
Description: If true, skips a task if the ```taskdir``` assigned to it exists.

**nthreads**<br />
Default: ```1```<br />
Description: Sets the number of parallel tasks to execute at once. Separate from execution parallelism.

**pbs_submitscript**<br />
Default: ```%(cwd)/pbs_submit.sh```<br />
Description: Sets the location of the PBS submission script. This script executes the commands to submit jobs to the scheduler. Job submission script must be handled in *file\** directives.

**pbs_subcommand**<br />
Default: ```qsub```<br />
Description: Sets the job scheduler submission command.

**nthreads**<br />
Default: ```1```<br />
Description: Sets the number of parallel tasks to execute at once. Separate from execution parallelism.

###Static parameters:

**cwd**<br />
Value: ```os.getcwd()```<br />
Description: Directory where chauffeur is executed in.

**scriptdir**<br />
Value: ```os.path.realpath(__file__)```<br />
Description: Directory where chauffeur lives.


## File\*
The ```file``` directive is used to specify files which should be processed. This may be used multiple times in the input. These are detected by searching for top-level directives which contain ```file```. When including multiple files, you must append unique suffices to ```file``` (e.g. ```file_1``` & ```file_2```).

### Modifiable parameters:

**input**<br />
Default: ```None```<br />
Description: Specify input file to be processed. Required if ```file``` directive is used.

**output**<br />
Default: ```None```<br />
Description: Specify resulting output file. Required if ```file``` directive is used.

**type**<br />
Default: ```None```<br />
Options: ```None```, ```pbs```<br />
Description: Specify type of file. If set to ```pbs```, this file will be used as the job scheduler submission script.

**parameters**<br />
Default: ```None```<br />
Description: Specify additional parameters related to this file. Parameters should be defined as subdirectives<br />
>parameters:<br />
>&nbsp;&nbsp;&nbsp;&nbsp;param1: "foo"<br />
>&nbsp;&nbsp;&nbsp;&nbsp;param2: "bar"<br />

## Run\*
The ```run``` directive is used to specify parameter space variables which specify the tasks to execute.

### Modifiable parameters:

**variables**<br />
Default: ```MUST BE DEFINED```<br />
Description: Specify the values of the parameter space to be combined. Individual variables should be defined as subdirectives.<br />
>variables:<br />
>&nbsp;&nbsp;&nbsp;&nbsp;var1: [1,2,3]<br />
>&nbsp;&nbsp;&nbsp;&nbsp;var2: ["foo","bar"]<br />

**variableorder**<br />
Default: ```None```<br />
Description: Specify the order that variables should be evaluated in the tensor product. Value should be a list containing the variable names, in order of fastest to slowest varying. By default, variables will be evaluated in lexicographical order.

**parameters**<br />
Default: ```None```<br />
Description: Specify additional parameters related to this task. Parameters should be defined as subdirectives<br />
>parameters:<br />
>&nbsp;&nbsp;&nbsp;&nbsp;param1: "foo"<br />
>&nbsp;&nbsp;&nbsp;&nbsp;param2: "bar"<br />

## Userdef\*
The ```userdef``` directive is used to specify parameters which are not directly tied to any task or file. Examples include mathematical expressions that may involve task/file-level parameters, instance-specific identifiers, etc. User defined parameters should be defined as subdirectives.
>userdef:<br />
>&nbsp;&nbsp;&nbsp;&nbsp;pi: 3.14159265<br />
>&nbsp;&nbsp;&nbsp;&nbsp;twopi: "\`2*%(pi)\`"<br />
