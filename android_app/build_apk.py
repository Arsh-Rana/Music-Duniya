#!/usr/bin/env python3
"""
Automated Android APK Builder for Music-Duniya
Builds a production-ready, signed Music-Duniya.apk using installed Android SDK and OpenJDK.
"""

import os
import sys
import shutil
import subprocess
import zipfile

def run_cmd(cmd, cwd=None):
    print(f"[*] Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    res = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Error: {res.stderr}\n{res.stdout}")
        sys.exit(res.returncode)
    return res.stdout

def build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    music_web_dir = os.path.join(root_dir, 'music_app')

    sdk_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Android', 'Sdk')
    build_tools_dir = os.path.join(sdk_dir, 'build-tools', '35.0.0')
    platforms_dir = os.path.join(sdk_dir, 'platforms', 'android-35')

    aapt2 = os.path.join(build_tools_dir, 'aapt2.exe')
    d8 = os.path.join(build_tools_dir, 'd8.bat')
    zipalign = os.path.join(build_tools_dir, 'zipalign.exe')
    apksigner = os.path.join(build_tools_dir, 'apksigner.bat')
    android_jar = os.path.join(platforms_dir, 'android.jar')

    print("[1] Verifying build toolchain...")
    for tool_name, tool_path in [('aapt2', aapt2), ('d8', d8), ('zipalign', zipalign), ('apksigner', apksigner), ('android.jar', android_jar)]:
        if not os.path.exists(tool_path):
            raise FileNotFoundError(f"Missing build tool: {tool_path}")
    print("  -> All SDK tools found.")

    # 1. Prepare assets
    print("[2] Syncing frontend web assets into assets/...")
    assets_dir = os.path.join(script_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    for f in ['index.html', 'style.css', 'app.js', 'songs.json', 'playlists_resolved.json', 'logo.png']:
        src = os.path.join(music_web_dir, f)
        dst = os.path.join(assets_dir, f)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"  Copied {f}")

    # 2. Compile resources
    print("[3] Compiling Android resources with AAPT2...")
    compiled_res = os.path.join(script_dir, 'compiled_res.zip')
    res_dir = os.path.join(script_dir, 'res')
    if os.path.exists(compiled_res):
        os.remove(compiled_res)
    run_cmd([aapt2, 'compile', '--dir', res_dir, '-o', compiled_res], cwd=script_dir)

    # 3. Link resources & package into unaligned APK
    print("[4] Linking APK with AAPT2...")
    unaligned_apk = os.path.join(script_dir, 'unaligned.apk')
    manifest = os.path.join(script_dir, 'AndroidManifest.xml')
    src_dir = os.path.join(script_dir, 'src')

    if os.path.exists(unaligned_apk):
        os.remove(unaligned_apk)

    link_cmd = [
        aapt2, 'link',
        '-I', android_jar,
        compiled_res,
        '--manifest', manifest,
        '-o', unaligned_apk,
        '--java', src_dir,
        '-A', assets_dir,
        '--auto-add-overlay'
    ]
    run_cmd(link_cmd, cwd=script_dir)

    # 4. Compile Java files
    print("[5] Compiling Java source files with javac...")
    obj_dir = os.path.join(script_dir, 'obj')
    if os.path.exists(obj_dir):
        shutil.rmtree(obj_dir)
    os.makedirs(obj_dir, exist_ok=True)

    java_files = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith('.java'):
                java_files.append(os.path.join(root, f))

    javac_cmd = [
        'javac',
        '-source', '17',
        '-target', '17',
        '-cp', android_jar,
        '-d', obj_dir
    ] + java_files
    run_cmd(javac_cmd, cwd=script_dir)

    # 5. Convert class files to Dalvik Executable (classes.dex) with d8
    print("[6] Converting classes to DEX with D8...")
    class_files = []
    for root, _, files in os.walk(obj_dir):
        for f in files:
            if f.endswith('.class'):
                class_files.append(os.path.join(root, f))

    dex_dir = os.path.join(script_dir, 'dex_out')
    if os.path.exists(dex_dir):
        shutil.rmtree(dex_dir)
    os.makedirs(dex_dir, exist_ok=True)

    d8_cmd = [d8, '--min-api', '26', '--output', dex_dir] + class_files
    run_cmd(d8_cmd, cwd=script_dir)

    classes_dex = os.path.join(dex_dir, 'classes.dex')
    if not os.path.exists(classes_dex):
        raise FileNotFoundError("D8 failed to produce classes.dex")

    # 6. Insert classes.dex into unaligned.apk
    print("[7] Packaging classes.dex into APK...")
    with zipfile.ZipFile(unaligned_apk, 'a') as apk:
        apk.write(classes_dex, arcname='classes.dex')

    # 7. Zipalign APK (4-byte alignment)
    print("[8] Aligning APK with zipalign...")
    aligned_apk = os.path.join(script_dir, 'music-duniya-aligned.apk')
    if os.path.exists(aligned_apk):
        os.remove(aligned_apk)
    run_cmd([zipalign, '-p', '-f', '4', unaligned_apk, aligned_apk], cwd=script_dir)

    # 8. Create debug keystore if not exists
    keystore = os.path.join(script_dir, 'debug.keystore')
    if not os.path.exists(keystore):
        print("[9] Generating debug signing keystore...")
        keytool_cmd = [
            'keytool', '-genkeypair',
            '-keystore', keystore,
            '-storepass', 'android',
            '-alias', 'androiddebugkey',
            '-keypass', 'android',
            '-keyalg', 'RSA',
            '-keysize', '2048',
            '-validity', '10000',
            '-dname', 'CN=Android Debug,O=Android,C=US'
        ]
        run_cmd(keytool_cmd, cwd=script_dir)

    # 9. Sign APK with apksigner
    print("[10] Signing APK with apksigner...")
    final_apk = os.path.join(root_dir, 'Music.apk')
    final_apk_duniya = os.path.join(root_dir, 'Music-Duniya.apk')
    final_apk_local = os.path.join(script_dir, 'Music.apk')
    final_apk_local_duniya = os.path.join(script_dir, 'Music-Duniya.apk')
    music_web_apk = os.path.join(music_web_dir, 'Music.apk')
    music_web_apk_duniya = os.path.join(music_web_dir, 'Music-Duniya.apk')

    for p in [final_apk, final_apk_duniya, final_apk_local, final_apk_local_duniya]:
        if os.path.exists(p):
            os.remove(p)

    sign_cmd = [
        apksigner, 'sign',
        '--ks', keystore,
        '--ks-pass', 'pass:android',
        '--out', final_apk,
        aligned_apk
    ]
    run_cmd(sign_cmd, cwd=script_dir)

    # Copy to all target locations for seamless access
    for dst in [final_apk_duniya, final_apk_local, final_apk_local_duniya, music_web_apk, music_web_apk_duniya]:
        shutil.copy2(final_apk, dst)

    # 10. Verify signature
    print("[11] Verifying APK signature...")
    verify_cmd = [apksigner, 'verify', '--verbose', final_apk]
    run_cmd(verify_cmd, cwd=script_dir)

    size_mb = os.path.getsize(final_apk) / (1024 * 1024)
    print("==================================================================")
    print(f"🎉 SUCCESS! APK Built Successfully!")
    print(f"📦 APK File: {final_apk}")
    print(f"📊 File Size: {size_mb:.2f} MB")
    print("==================================================================")

if __name__ == '__main__':
    build()
