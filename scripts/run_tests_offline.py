"""Run pytest without provider credentials or Python socket network access.

Usage: python scripts/run_tests_offline.py [--uvloop] [--observe] [pytest arguments]
Use --uvloop only where the sandbox blocks asyncio's local socket wakeup.
"""
import asyncio
import os
from pathlib import Path
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    if (root / '.env').exists():
        raise SystemExit('Offline tests require a checkout without .env')
    os.chdir(root)
    sys.path.insert(0, str(root))
    arguments = sys.argv[1:]
    observe = '--observe' in arguments
    if observe:
        arguments.remove('--observe')
    for name in list(os.environ):
        if name.startswith('OBS_'):
            os.environ.pop(name)
    os.environ.update(
        GEMINI_API_KEY='', GOOGLE_API_KEY='', OPENAI_API_KEY='', ANTHROPIC_API_KEY='',
        CREWAI_TELEMETRY_DISABLED='true', OTEL_SDK_DISABLED='true',
        DO_NOT_TRACK='true', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
        OBS_ENABLED='true' if observe else 'false', OBS_EXECUTION_MODE='mock',
        OBS_STORE_ENABLED='false',
    )
    sys.dont_write_bytecode = True
    if '--uvloop' in arguments:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        arguments.remove('--uvloop')

    blocked = []
    def guard(event, args):
        if event in {'socket.connect', 'socket.getaddrinfo', 'socket.sendto'}:
            blocked.append(event)
            raise RuntimeError('Offline test runner blocked network access')
    sys.addaudithook(guard)

    with tempfile.TemporaryDirectory(prefix='knowledgeflow-tests-') as directory:
        os.environ['XDG_DATA_HOME'] = directory
        os.environ['CREWAI_STORAGE_DIR'] = directory
        import pytest
        result = pytest.main(['-q', '-p', 'no:cacheprovider', *arguments])
    print(f'OFFLINE_NETWORK_ATTEMPTS_BLOCKED={len(blocked)}')
    # A swallowed network error must still fail the offline run.
    return result or (1 if blocked else 0)


if __name__ == '__main__':
    raise SystemExit(main())
