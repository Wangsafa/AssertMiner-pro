# AssertMiner-pro

This repository contains the implementation of the techniques proposed in the paper:

**AssertMiner-pro: Enhanced Module-Level Spec Generation and Assertion Mining with LLM Guided by Top-Down Hierarchical Strategies**

This tool automatically generates module-level formal specifications for RTL designs using LLMs.
It is designed for hierarchical, top-down specification extraction, leveraging call trees, RTL code, IO ports, and signal dependency information.

The script traverses multiple RTL designs, analyzes their module hierarchy, and generates layer-by-layer specifications from the top module down to leaf modules.

The script assumes the following fixed project layout:

## Project Structure

```text
assertminer-pro/
├── benchmark/
│   ├── rtl/
│   │   ├── design_1/
│   │   ├── design_2/
│   │   └── ...
│   └── spec_md/
│       ├── design_1.md
│       ├── design_2.md
│       └── ...
│
├── result_log/
│   ├── design_1/
│   │   ├── rtl/
│   │   │   ├── top.v
│   │   │   ├── submodule1.v
│   │   │   └── ...
│   │   ├── IO_port/
│   │   │   ├── top.txt
│   │   │   ├── submodule1.txt
│   │   │   └── ...
│   │   ├── call_tree.txt
│   │   ├── signal_chains.txt
│   │   ├── module_list.txt        (optional)
│   │   └── generated_spec/
│   └── design_2/
│       └── ...
│
├── spec_extraction_prompt.txt
└── assertminer-pro.py
```
## File Descriptions
### 1. call_tree.txt
Defines the module hierarchy using indentation (tabs or 2 spaces per level):
```text
top
  submodule1
    submodule1_1
  submodule2
```
This file is used to determine parent–child relationships and call paths between modules.

### 2. benchmark/spec_md/<design>.md
Top-level specification for the design.
This file provides global semantic context and is included when generating specifications for all submodules.

### 3. result_log/\<design\>/rtl/
Contains per-module extracted RTL source files:
```text
top.v
submodule1.v
submodule2.v
```

### 4. result_log/\<design\>/IO_port/\<module\>.txt
Textual description of the IO ports of each module, for example:
```text
input        clk
input        reset
input  [31:0] data_in
output       done
```
This information is used to guide interface-level semantic understanding of the target module.

### 5. signal_chains.txt
Describes inter-module and intra-module signal propagation paths, for example:
```text
i2c_master_top.wb_clk_i > i2c_master_byte_ctrl.clk > i2c_master_bit_ctrl.clk
```
This file provides additional structural and semantic cues to help the LLM infer dataflow and control dependencies.

### 6. module_list.txt (Optional)
If present, only the modules listed in this file will have specifications generated:
```text
topmodule_name
submodule1_name
submodule2_name
```
If this file is absent, all modules in the call tree will be processed by default.

### 7. spec_extraction_prompt.txt
The LLM prompt template that instructs how module-level specifications should be written.

This file is passed directly to the model as the user prompt, while structural and design information is provided as context.
