"""运行库内功绩研究源码；冻结副本、结果与日志只写仓库外。

研究目录保留各自的局部导入。执行前按原相邻目录名冻结源码，使既有
模型与来源摘要逐字节不变；复核只比较版本，不覆盖旧副本或重写结果。
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
FOLDERS = {
    'baseline': 'merit-study',
    'buffers': 'merit-buffer-study',
    'occupancy': 'merit-occupancy-study',
    'controller': 'merit-controller-study',
    'joint': 'merit-joint-study',
}
RUNS = {
    'baseline': [['study.py']],
    'buffers': [['explore.py']],
    'occupancy': [['static.py'], *[['simulate.py', '--seed', str(i)] for i in range(4)], ['aggregate.py']],
    'controller': [['study.py']],
    'joint': [['mapping_audit.py'], ['study.py', '--phase', 'pilot'], ['study.py', '--phase', 'validation']],
}
CHECKS = {
    'baseline': [['checks.py']],
    'buffers': [['checks.py']],
    'occupancy': [['-m', 'unittest', 'discover', '-s', '.', '-p', '*checks.py']],
    'controller': [['-m', 'unittest', 'discover', '-s', '.', '-p', 'checks.py']],
    'joint': [['-m', 'unittest', 'discover', '-s', '.', '-p', '*checks.py']],
}


def selection(study):
    """占职依赖缓冲研究源码及其封存结果，必须先执行依赖。"""
    if study == 'joint':
        return ['buffers', 'occupancy', 'controller', 'joint']
    return list(FOLDERS) if study == 'all' else ['buffers', 'occupancy'] if study == 'occupancy' else [study]


def digest(path):
    """计算实际文件摘要，路径只在调用端解释。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def outside_repository(path):
    """解析符号链接后检查产物边界，避免把结果混进版本库。"""
    path = path.resolve()
    if path == REPO or REPO in path.parents:
        raise ValueError('产物目录必须位于仓库外')
    return path


def sources(study):
    """研究源码不含结果、缓存和运行日志；各组采用独立进程导入。"""
    return sorted((ROOT / study).glob('*.py'))


def prepare(output, studies):
    """创建新冻结副本；非空目录一律拒绝，保留已有证据。"""
    if output.exists() and any(output.iterdir()):
        raise ValueError('新运行的产物目录必须为空；复核旧结果请使用 --check-only')
    output.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for study in studies:
        target = output / FOLDERS[study]
        target.mkdir()
        for source in sources(study):
            shutil.copyfile(source, target / source.name)
            manifest[f'{FOLDERS[study]}/{source.name}'] = {
                'repository_source': source.relative_to(REPO).as_posix(), 'sha256': digest(source),
            }
    (output / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


def verify_snapshot(output, studies, result_studies=None):
    """复核当前源码与旧冻结版本一致，不写回或自动刷新摘要。"""
    required = set(studies if result_studies is None else result_studies)
    for study in studies:
        target = output / FOLDERS[study]
        expected = {source.name for source in sources(study)}
        actual = {source.name for source in target.glob('*.py')}
        if actual != expected:
            raise ValueError(f'源码不一致：{study} 文件集合不同')
        for source in sources(study):
            if digest(source) != digest(target / source.name):
                raise ValueError(f'源码不一致：{study}/{source.name}')
        if study not in required:
            continue
        result = target / 'results.json'
        if not result.is_file():
            raise ValueError(f'缺少研究结果：{study}/results.json')
        seal = json.loads(result.read_text(encoding='utf-8'))['source_sha256']
        if isinstance(seal, str):
            seal = {'study.py': seal}
        for name, expected_hash in seal.items():
            if digest(target / name) != expected_hash:
                raise ValueError(f'结果来源不一致：{study}/{name}')


def execute(output, study, args, index, phase):
    """每步记录独立日志；失败停止，不把部分完成冒充整组通过。"""
    logs = output / 'run-logs'
    logs.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix=f'{study}-{phase}-{index}-',
                                     suffix='.log', dir=logs, delete=False) as stream:
        log = Path(stream.name)
        completed = subprocess.run([sys.executable, *args], cwd=output / FOLDERS[study], stdout=stream, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError(f'{study} 执行失败（退出码{completed.returncode}），见 {log}\n{log.read_text(encoding="utf-8")[-4000:]}')
    print(f'{study}: {phase} {index} 通过', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', choices=[*FOLDERS, 'all'])
    parser.add_argument('--output-dir', type=Path, help='仓库外产物目录；默认新建系统临时目录')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-only', action='store_true', help='只冻结源码，不运行演算')
    mode.add_argument('--check-only', action='store_true', help='核对已有产物与当前源码并运行研究检查')
    args = parser.parse_args(argv)
    try:
        if args.check_only and args.output_dir is None:
            raise ValueError('--check-only 必须指定已有 --output-dir')
        output = outside_repository(args.output_dir or Path(tempfile.mkdtemp(prefix='tca-merit-research-')))
        studies = selection(args.study)
        executing = ['joint'] if args.study == 'joint' else studies
        if args.check_only:
            verify_snapshot(output, studies, executing)
        else:
            prepare(output, studies)
        print(f'研究产物：{output}', flush=True)
        if args.prepare_only:
            return 0
        if not args.check_only:
            for study in executing:
                for index, command in enumerate(RUNS[study], 1):
                    execute(output, study, command, index, 'run')
            verify_snapshot(output, studies, executing)
        for study in executing:
            for index, command in enumerate(CHECKS[study], 1):
                execute(output, study, command, index, 'check')
        print('研究检查通过；不代表游戏引擎验收。')
        return 0
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
