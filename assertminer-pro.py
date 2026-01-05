"""
Auto-generate module-level specifications for all designs.

Features:
- Traverse all designs under benchmarks/rtl/
- Parse module call tree
- Generate specifications layer-by-layer (top -> leaf)
- Use extracted per-module RTL from result_log/<design>/rtl/
- Each module spec is generated with:
    * top-level spec
    * parent module specs
    * RTL code along call path
    * module IO ports
    * signal chains
"""

import os
from pathlib import Path
from openai import OpenAI
import openai

# ============================================================
# OpenAI Wrapper
# ============================================================

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['HF_HUB_HTTPS_PROXY'] = ''


class GPT4oModel:
    def __init__(self, api_key: str):
        openai.api_key = api_key

    def generate_response(self, system_content: str, context: str, user_content: str) -> str:
        client = OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="",
            messages=[
                {'role': 'system', 'content': system_content},
                {'role': 'assistant', 'content': context}, 
                {'role': 'user', 'content': user_content}
            ],
            temperature=0
        )
        return response.choices[0].message.content



# ============================================================
# File Utils
# ============================================================
def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk")


# ============================================================
# Call Tree Parsing
# ============================================================
def parse_tree_from_file(file_path: Path):
    tree = {}
    stack = [(0, tree)]
    with file_path.open("r") as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped:
                continue

            line_expanded = line.replace('\t', '  ')
            level = (len(line_expanded) - len(line_expanded.lstrip(" "))) // 2
            module = line_expanded.strip()
            node = {}

            while stack and stack[-1][0] >= level:
                stack.pop()

            if not stack:
                parent = tree
                stack.append((0, tree))
            else:
                parent = stack[-1][1]

            parent[module] = node
            stack.append((level, node))
    return tree



def find_path(tree, target, path=None):
    if path is None:
        path = []
    for module, subtree in tree.items():
        cur = path + [module]
        if module == target:
            return cur
        res = find_path(subtree, target, cur)
        if res:
            return res
    return None


def flatten_tree(tree):
    res = []
    for k, v in tree.items():
        res.append(k)
        res.extend(flatten_tree(v))
    return res


# ============================================================
# RTL Collection
# ============================================================
def collect_rtl_code(rtl_dir: Path, modules):
    codes = []
    for m in modules:
        vfile = rtl_dir / f"{m}.v"
        if vfile.exists():
            codes.append(
                f"// ==================================================\n"
                f"// RTL of module: {m}\n"
                f"// ==================================================\n"
                f"{read_file(vfile)}"
            )
    return "\n\n".join(codes)


# ============================================================
# Main Per-Design Pipeline
# ============================================================
def generate_specs_for_design(design: str, gpt: GPT4oModel, target_modules=None):
    """
    target_modules: list of module names to generate spec for.
                    If None, generate for all modules.
    """
    base = Path("Your_path_to_this_project/assertminer-pro")

    rtl_dir = base / "result_log" / design / "rtl"
    io_dir = base / "result_log" / design / "IO_port"
    signal_chain_file = base / "result_log" / design / "signal_chains.txt"
    out_dir = base / "result_log" / design / "generated_spec"
    out_dir.mkdir(parents=True, exist_ok=True)

    call_tree_file = base / "result_log" / design / "call_tree.txt"
    top_spec_file = base / "benchmarks/spec_md" / f"{design}.md"
    prompt_file = base / "spec_extraction_prompt.txt"

    if not call_tree_file.exists():
        print(f"[SKIP] {design}: call_tree.txt not found")
        return

    print(f"\n========== Processing design: {design} ==========")

    call_tree = parse_tree_from_file(call_tree_file)
    all_modules = flatten_tree(call_tree)

    top_spec = read_file(top_spec_file)
    signal_chains = read_file(signal_chain_file)
    prompt = read_file(prompt_file)

    system_msg = (
        "You are an expert in RTL design and formal specification writing. "
        "Generate a precise specification for target module."
    )

    generated_specs = {}

    # 如果没有传 target_modules，则生成所有模块
    if target_modules is None:
        modules_to_generate = all_modules
    else:
        modules_to_generate = target_modules

    for module in modules_to_generate:
        print(f"  → Generating spec for module: {module}")

        path = find_path(call_tree, module)
        if not path:
            print(f"    [WARN] {module} not found in call tree")
            continue

        parent_specs = []
        for p in path[:-1]:
            if p in generated_specs:
                parent_specs.append(
                    f"### Specification of {p}\n{generated_specs[p]}"
                )

        rtl_code = collect_rtl_code(rtl_dir, path)
        io_ports = read_file(io_dir / f"{module}.txt")

        context = f"""
### Target Module Name ###
{module}

### Top-Level Specification ###
{top_spec}

##### Specifications of Parent Modules ###
{'\n\n'.join(parent_specs)}

### RTL Code of Modules on Call Path ###
{rtl_code}

### IO Ports of Target Module ({module}) ###
{io_ports}

### Signal Chains ###
{signal_chains}
"""

        spec = gpt.generate_response(system_msg, context, prompt)
        generated_specs[module] = spec

        (out_dir / f"{module}.md").write_text(spec, encoding="utf-8")



def read_target_modules(design: str):
    base = Path("Your_path_to_this_project/assertminer-pro")
    module_list_file = base / "result_log" / design / "module_list.txt"
    if not module_list_file.exists():
        print(f"  [WARN] {module_list_file} not found, defaulting to all modules")
        return None  
    modules = [line.strip() for line in module_list_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return modules


# ============================================================
# Entry
# ============================================================
def main():

    gpt = GPT4oModel(api_key="")

    rtl_root = Path("Your_path_to_this_project/benchmarks/rtl")

    for design_dir in rtl_root.iterdir():
        if design_dir.is_dir():
            target_modules = read_target_modules(design_dir.name)
            generate_specs_for_design(design_dir.name, gpt, target_modules=target_modules)

if __name__ == "__main__":
    main()
