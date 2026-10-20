#!/usr/bin/env python3
import os, sys
binary = '/opt/homebrew/bin/omp'
os.execv(binary, [binary, '--model', '__call_omp_failure_probe_nonexistent__', *sys.argv[1:]])
