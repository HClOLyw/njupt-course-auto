# -*- coding: utf-8 -*-
import os
d = r"D:\part time cx\njupt-gui\dist"
print("dist exists:", os.path.isdir(d))
if os.path.isdir(d):
    for n in os.listdir(d):
        p = os.path.join(d, n)
        print(repr(n), "dir" if os.path.isdir(p) else "file", os.path.getsize(p) if os.path.isfile(p) else "")
g = r"D:\part time cx\njupt-gui"
print("--- njupt-gui root ---")
for n in os.listdir(g):
    p = os.path.join(g, n)
    if os.path.isfile(p) and n.lower().endswith((".exe", ".spec")):
        print(repr(n), os.path.getsize(p))
