# สร้างไฟล์เสียงผู้หญิง สไตล์นักบวชปีศาจ จาก voice-script.csv ลงโฟลเดอร์ ../voice
# ติดตั้งครั้งแรก:  pip install edge-tts     และติดตั้ง ffmpeg (ใช้ทำเสียงปีศาจ):  winget install Gyan.FFmpeg
# คำสั่ง:
#   python make_voice.py --test       สร้างตัวอย่างหลายแบบไว้ฟังเลือก (ไฟล์ _test_*.mp3 ในโฟลเดอร์ voice)
#   python make_voice.py              สร้างครบทุกประโยค (ข้ามไฟล์ที่มีแล้ว)
#   python make_voice.py --force      สร้างใหม่ทับทั้งหมดหลังแก้ค่า
#   python make_voice.py --voices     ดูรายชื่อเสียงไทยที่มี
#   --mode demon|deep|soft|none       เลือกเอฟเฟกต์ (ค่าตั้งต้น demon)
import asyncio, csv, os, shutil, subprocess, sys
import edge_tts

VOICE = "th-TH-PremwadeeNeural"   # เสียงผู้หญิงไทย
RATE = "-22%"                     # ยิ่งติดลบยิ่งช้า
PITCH = "-2Hz"                    # ติดลบมากเสียงอาจฟังเหมือนผู้ชาย
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "voice")

# เสียงเดิม + เสียงซ้อนที่ต่ำลง (ปีศาจพูดซ้อนกัน) + ก้อง
FX = {
    "soft": "aecho=0.8:0.88:90|180:0.35|0.2,volume=1.3",
    "demon": "[0:a]aresample=44100,asplit=2[a][b];[b]asetrate=44100*0.72,aresample=44100,atempo=1.388889[low];"
             "[a][low]amix=inputs=2:weights=1 1,aecho=0.8:0.88:60|130:0.4|0.3,volume=1.9",
    "deep": "[0:a]aresample=44100,asplit=2[a][b];[b]asetrate=44100*0.62,aresample=44100,atempo=1.612903[low];"
            "[a][low]amix=inputs=2:weights=1 1.2,aecho=0.8:0.9:70|150:0.45|0.3,acrusher=bits=10:mode=log:aa=1,volume=1.9",
}
# ค่าความเร็ว/ความทุ้มของแต่ละโหมด (ตรงกับไฟล์ตัวอย่าง _test_ ที่ฟัง)
MODE_PARAMS = {"deep": ("-28%", "-4Hz")}
mode = "demon"
if "--mode" in sys.argv:
    mode = sys.argv[sys.argv.index("--mode") + 1]
if "--nofx" in sys.argv:
    mode = "none"
if mode != "none" and not shutil.which("ffmpeg"):
    print("ไม่พบ ffmpeg จึงสร้างเสียงเปล่าไม่มีเอฟเฟกต์ปีศาจ (ติดตั้งด้วย: winget install Gyan.FFmpeg แล้วเปิด PowerShell ใหม่)")
    mode = "none"

async def render(text, path, rate, pitch, fxmode):
    raw = path if fxmode == "none" else path + ".raw.mp3"
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch).save(raw)
            break
        except Exception as e:
            if attempt == 2:
                print("ล้มเหลว", os.path.basename(path), e); return False
            await asyncio.sleep(2)
    if fxmode != "none":
        f = FX[fxmode]
        args = ["ffmpeg", "-v", "error", "-y", "-i", raw]
        args += (["-filter_complex", f] if f.startswith("[") else ["-af", f]) + [path]
        subprocess.run(args, check=False)
        os.remove(raw)
    return True

async def one(id_, text, sem):
    path = os.path.join(OUT, id_ + ".mp3")
    if os.path.exists(path) and "--force" not in sys.argv:
        return
    async with sem:
        rt, pt = MODE_PARAMS.get(mode, (RATE, PITCH))
        if await render(text, path, rt, pt, mode):
            print("ok", id_)

async def main():
    os.makedirs(OUT, exist_ok=True)
    if "--voices" in sys.argv:
        for v in await edge_tts.list_voices():
            if v["Locale"].startswith("th"):
                print(v["ShortName"], v["Gender"])
        return
    if "--test" in sys.argv:
        text = "ม่านหมอกเปิดออกแล้ว ไพ่ได้เลือกเจ้าของมันแล้ว จงฟังให้ดี"
        laugh = "ฮ่า ฮ่า ฮ่า ฮ่า ฮ่า ฮ่า"
        tests = [("a_plain", text, "-20%", "+0Hz", "none"), ("b_soft", text, RATE, PITCH, "soft"),
                 ("c_demon", text, RATE, PITCH, "demon"), ("d_deep", text, "-28%", "-4Hz", "deep"),
                 ("e_laugh_demon", laugh, "-10%", PITCH, "demon"), ("f_laugh_deep", laugh, "-15%", "-4Hz", "deep")]
        for name, tx, rt, pt, fm in tests:
            if fm != "none" and not shutil.which("ffmpeg"):
                continue
            await render(tx, os.path.join(OUT, "_test_" + name + ".mp3"), rt, pt, fm)
            print("สร้างตัวอย่าง _test_" + name + ".mp3")
        return
    with open(os.path.join(HERE, "voice-script.csv"), encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    sem = asyncio.Semaphore(4)
    await asyncio.gather(*[one(r["id"], r["text"], sem) for r in rows])
    print("เสร็จแล้ว (โหมด", mode + ") ไฟล์อยู่ที่", os.path.abspath(OUT))

asyncio.run(main())
