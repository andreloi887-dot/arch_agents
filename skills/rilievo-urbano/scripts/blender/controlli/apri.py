"""apre un .blend e lancia uno script della filiera: python apri.py <file.blend> <script.py> -- argomenti"""
import sys, runpy, bpy
blend, script = sys.argv[1], sys.argv[2]
bpy.ops.wm.open_mainfile(filepath=blend)
sys.argv = [script] + sys.argv[3:]
runpy.run_path(script, run_name="__main__")
