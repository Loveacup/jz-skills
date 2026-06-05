#!/usr/bin/env python3
"""Auto-Diary Data Collector v3.2 — CC: entrypoint+parentUuid 三分类.
Source of truth: ~/code/jz-skills/hermes/auto-diary/scripts/collect_data.py
"""
import ast, json, os, sys, subprocess, signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

WEEKDAY_CN = ["周一","周二","周三","周四","周五","周六","周日"]

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def get_weekday(date_str):
    try: return WEEKDAY_CN[datetime.strptime(date_str,"%Y-%m-%d").weekday()]
    except: return "未知"

def get_weather(date_str=None):
    codes={0:"☀️ 晴",1:"🌤 多云",2:"🌤 多云",3:"☁️ 阴",45:"🌫 雾",48:"🌫 雾凇",51:"🌦 毛毛雨",53:"🌦 小雨",55:"🌧 中雨",61:"🌧 小雨",63:"🌧 中雨",65:"🌧 大雨",71:"🌨 小雪",73:"🌨 中雪",75:"🌨 大雪",80:"🌦 阵雨",81:"🌦 阵雨",82:"🌧 暴雨",95:"⛈ 雷雨",96:"⛈ 雷暴伴冰雹",99:"⛈ 雷暴伴冰雹"}
    try:
        if date_str:
            url=f"https://archive-api.open-meteo.com/v1/archive?latitude=30.27&longitude=120.16&start_date={date_str}&end_date={date_str}&daily=temperature_2m_mean,weathercode&timezone=Asia/Shanghai"
            r=subprocess.run(["curl","-s","-m","10",url],capture_output=True,text=True,timeout=15)
            if r.returncode==0 and r.stdout.strip():
                d=json.loads(r.stdout);daily=d.get("daily",{})
                if daily.get("temperature_2m_mean") and daily.get("weathercode"):
                    return f"杭州: {codes.get(daily['weathercode'][0],'🌡')} {daily['temperature_2m_mean'][0]}°C"
        else:
            r=subprocess.run(["curl","-s","-m","10","https://api.open-meteo.com/v1/forecast?latitude=30.27&longitude=120.16&current_weather=true"],capture_output=True,text=True,timeout=15)
            if r.returncode==0 and r.stdout.strip():
                d=json.loads(r.stdout);cw=d.get("current_weather",{})
                return f"杭州: {codes.get(cw.get('weathercode',-1),'🌡')} {cw.get('temperature','?')}°C"
    except: pass
    for _ in range(2):
        try:
            r=subprocess.run(["curl","-s","-m","8","wttr.in/Hangzhou?format=杭州:+%c+%t+%h"],capture_output=True,text=True,timeout=12)
            if r.returncode==0 and r.stdout.strip() and "Unknown" not in r.stdout: return r.stdout.strip()
        except: pass
    return "天气获取失败"

def get_calendar_events(date_str):
    try:
        dt=datetime.strptime(date_str,"%Y-%m-%d")
        r=subprocess.run(["icalBuddy","-ic","个人1,工作1,Naomi1,Zelda1","-li","-ea","-nrd",f"eventsFrom:{dt.strftime('%Y-%m-%d')}T00:00:00",f"to:{dt.strftime('%Y-%m-%d')}T23:59:59"],capture_output=True,text=True,timeout=5)
        if r.returncode!=0: return []
        events=[];current=None
        for line in r.stdout.strip().split('\n'):
            line=line.rstrip()
            if not line: continue
            if line.startswith('• '):
                if current: events.append(current)
                content=line[2:]
                if '(' in content and content.endswith(')'):
                    lp=content.rfind('(');summary=content[:lp].strip();calendar=content[lp+1:-1].strip()
                else: summary=content;calendar="未知"
                current={"calendar":calendar,"summary":summary,"time":"","location":"","notes":""}
            elif line.startswith('    ') and 'at' in line:
                if current:
                    ts=line.strip()
                    if ' at ' in ts: ts=ts.split(' at ')[-1]
                    ts=ts.replace('today at ','').replace('tomorrow at ','').replace('yesterday at ','').replace('day before yesterday at ','')
                    current["time"]=ts
            elif line.startswith('    location:') and current: current["location"]=line.replace('    location:','').strip()
            elif line.startswith('    notes:') and current: current["notes"]=line.replace('    notes:','').strip()
            elif line.startswith('           ') and current and current.get("notes"): current["notes"]+=" "+line.strip()
        if current: events.append(current)
        return events
    except subprocess.TimeoutExpired: print("Calendar timeout",file=sys.stderr);return []
    except Exception as e: print(f"Calendar error: {e}",file=sys.stderr);return []

def _parse_cc_message(msg_raw):
    if isinstance(msg_raw,dict): return msg_raw
    if isinstance(msg_raw,str):
        try: return ast.literal_eval(msg_raw)
        except: return {}
    return {}

def _extract_cc_text(content):
    if isinstance(content,str): return content
    if isinstance(content,list):
        parts=[]
        for item in content:
            if isinstance(item,dict) and item.get("type")=="text": parts.append(item.get("text",""))
        return " ".join(parts)
    return str(content)

def extract_cc_summary(date_str):
    """Extract CC session summaries. Classifies via entrypoint + parentUuid + subagent detection."""
    shanghai=ZoneInfo("Asia/Shanghai");target_date=datetime.strptime(date_str,"%Y-%m-%d").date()
    cc_projects=Path.home()/".claude"/"projects"
    if not cc_projects.exists(): return []
    try:
        r=subprocess.run(["find",str(cc_projects),"-name","*.jsonl","-newermt",f"{date_str} 00:00","!","-newermt",f"{date_str} 23:59","-type","f"],capture_output=True,text=True,timeout=10)
        candidate_files=[f for f in r.stdout.strip().split("\n") if f]
    except: return []
    if not candidate_files: return []
    skip=( "[System note:","[Replying to:","[IMPORTANT:","[CONTEXT COMPACTION","Your task is to",
           "<local-command-caveat>","<command-name>","<command-message>","<observed_from_primary_session>","<local-command-stdout>",
           "You are a Claude-Mem","You are an AI assistant","You are a specialized","--- MODE SWITCH:","[Request interrupted",)
    
    # Phase 1: Collect metadata
    session_meta={}
    for fp in candidate_files:
        try:
            ep=None;muid=None;puid=None;is_sub="/subagents/" in fp
            with open(fp,encoding="utf-8") as f:
                for line in f:
                    try: entry=json.loads(line.strip())
                    except: continue
                    if entry.get("type")=="user":
                        msg=_parse_cc_message(entry.get("message",""))
                        if not msg: continue
                        txt=_extract_cc_text(msg.get("content",""))
                        if not txt or any(txt.startswith(p) for p in skip): continue
                        ep=entry.get("entrypoint","unknown");muid=entry.get("uuid");puid=entry.get("parentUuid");break
            if ep and muid: session_meta[fp]={"entrypoint":ep,"uuid":muid,"parentUuid":puid,"is_subagent":is_sub}
        except: continue
    
    # Phase 2: Build relationship graph
    uuid_to_file={m["uuid"]:fp for fp,m in session_meta.items()}
    has_children=set();has_parent=set()
    for fp,m in session_meta.items():
        if m["is_subagent"]:
            has_parent.add(fp)
            p=Path(fp)
            for anc in p.parents:
                pf=str(anc)+".jsonl"
                if pf in session_meta: has_children.add(pf);break
        puid=m["parentUuid"]
        if puid and puid in uuid_to_file: has_parent.add(fp);has_children.add(uuid_to_file[puid])
    
    # Phase 3: Classify and build summaries
    summaries=[]
    for fp in candidate_files:
        try:
            user_texts=[];ac=0;model="unknown";cwd="";ssu=None
            with open(fp,encoding="utf-8") as f:
                for line in f:
                    try: entry=json.loads(line.strip())
                    except: continue
                    et=entry.get("type","");ts=entry.get("timestamp","")
                    if et=="user":
                        msg=_parse_cc_message(entry.get("message",""))
                        if not msg: continue
                        txt=_extract_cc_text(msg.get("content",""))
                        if not txt or any(txt.startswith(p) for p in skip): continue
                        if ssu is None and ts:
                            try: ssu=datetime.fromisoformat(ts.replace("Z","+00:00"))
                            except: pass
                        user_texts.append(txt.strip().split("\n")[0][:80])
                        if not cwd: cwd=entry.get("cwd","")
                    elif et=="assistant":
                        ac+=1
                        if model=="unknown":
                            msg=_parse_cc_message(entry.get("message",""))
                            if msg: model=msg.get("model","unknown")
            if not user_texts or ssu is None: continue
            sl=ssu.astimezone(shanghai)
            if sl.date()!=target_date: continue
            pl=Path(cwd).name if cwd else Path(fp).parent.parent.name
            m=session_meta.get(fp,{})
            if fp in has_parent or fp in has_children: st="agent-team"
            elif m.get("entrypoint","").startswith("sdk"): st="program-call"
            else: st="standalone"
            summaries.append({"project":pl,"session_start":sl.strftime("%H:%M"),"model":model,"session_type":st,
                             "message_count":len(user_texts)+ac,"user_turns":len(user_texts),
                             "topics":[t for t in user_texts[:3] if t],
                             "summary":f"{len(user_texts)} 轮对话，模型 {model}"+(f"，涉及: {', '.join(user_texts[:2])}" if user_texts else "")})
        except: continue
    summaries.sort(key=lambda x:x["session_start"])
    return summaries

def build_cc_overview(summaries):
    if not summaries: return None
    def grp(items):
        if not items: return None
        prj={}
        for s in items:
            p=s["project"]
            if p not in prj: prj[p]={"sessions":0,"topics":[]}
            prj[p]["sessions"]+=1;prj[p]["topics"].extend(s["topics"])
        sp={p:{"sessions":d["sessions"],"topics":list(dict.fromkeys(d["topics"]))[:3]} for p,d in sorted(prj.items(),key=lambda x:-x[1]["sessions"])}
        return {"session_count":len(items),"message_count":sum(s["message_count"] for s in items),"user_turns":sum(s["user_turns"] for s in items),"projects":sp}
    return {"label":"Claude Code","total":grp(summaries),
            "agent_team":grp([s for s in summaries if s.get("session_type")=="agent-team"]),
            "standalone":grp([s for s in summaries if s.get("session_type")=="standalone"]),
            "program_call":grp([s for s in summaries if s.get("session_type")=="program-call"])}

def format_cc_for_diary(summaries):
    ov=build_cc_overview(summaries)
    if not ov or not ov.get("total"): return ""
    total=ov["total"]
    lines=["### 💻 Claude Code 工作概览",f"- 总会话: {total['session_count']} · 消息: {total['message_count']} · 轮次: {total['user_turns']}"]
    for key,el in [("agent_team","🤝 Agent Team 协作"),("program_call","🤖 程序调用"),("standalone","💻 独立对话")]:
        g=ov.get(key)
        if g:
            lines.append(f"\n#### {el}（{g['session_count']} 会话）")
            for proj,data in g["projects"].items(): lines.append(f"- **{proj}** ({data['sessions']}): {'；'.join(t[:60] for t in data['topics'])}")
    return "\n".join(lines)

def get_ai_logs(date_str):
    ai={"hermes":[],"claude":[]}
    sp=Path(__file__).parent;sys.path.insert(0,str(sp))
    try:
        from extract_hermes_conversations import build_profile_overview,extract_hermes_summary,format_for_diary
        hd=extract_hermes_summary(date_str);ai["hermes"]=hd;ai["hermes_overview"]=build_profile_overview(hd);ai["hermes_formatted"]=format_for_diary(hd)
    except Exception as e: print(f"Hermes extraction error: {e}",file=sys.stderr)
    try:
        cd=extract_cc_summary(date_str);ai["claude"]=cd;ai["claude_overview"]=build_cc_overview(cd);ai["claude_formatted"]=format_cc_for_diary(cd)
    except Exception as e: print(f"CC extraction error: {e}",file=sys.stderr)
    return ai

def read_file_safe(path,timeout_secs=3):
    try:
        if not os.path.exists(str(path)): return None
        signal.signal(signal.SIGALRM,timeout_handler);signal.alarm(timeout_secs)
        try:
            with open(path,encoding='utf-8') as f: content=f.read()
            signal.alarm(0);return content
        except TimeoutError: return None
        finally: signal.alarm(0)
    except: pass
    return None

def scan_vault_changes(vault_root,date_str):
    try:
        r=subprocess.run(["find",str(vault_root),"-name","*.md","-newermt",f"{date_str} 00:00","!","-newermt",f"{date_str} 23:59","-type","f"],capture_output=True,text=True,timeout=15)
        if r.returncode!=0: return []
        changes=[]
        for fp in r.stdout.strip().split('\n'):
            if not fp: continue
            if any(d in fp for d in ("/01_日记/","/000_日记/","/88_event-bridge/","/99-System/")): continue
            if len(changes)>=100: break
            try: rp=str(Path(fp).relative_to(vault_root))
            except: continue
            try:
                with open(fp,encoding='utf-8') as f:
                    fl=f.readline().strip();title=fl[2:] if fl.startswith('# ') else Path(fp).stem
            except: title=Path(fp).stem
            changes.append({"path":rp,"type":"新建/修改","title":title})
        return changes
    except: return []

def sync_obsidian():
    sp=Path(__file__).parent;sys.path.insert(0,str(sp))
    try:
        from obsidian_sync import sync_and_wait;return sync_and_wait()
    except Exception as e: return {"status":"error","message":f"Obsidian 同步失败: {e}"}

def get_dingtalk_class_msgs(date_str):
    """读取钉钉班级群每日消息文件"""
    p=Path.home()/f".hermes/data/dingtalk_class_msgs/{date_str}.txt"
    content=read_file_safe(p)
    if content and len(content.strip())>50:
        return {"status":"ok","content":content,"path":str(p)}
    return {"status":"empty"}

def collect_diary_data(date_str):
    dp=Path.home()/"Documents/Obsidian/AlexCai/50-Self/01_日记"/f"{date_str}.md"
    vr=Path.home()/"Documents/Obsidian/AlexCai"
    return {"date":date_str,"weekday":get_weekday(date_str),"weather":get_weather(date_str),
            "ai_logs":get_ai_logs(date_str),"calendar_events":get_calendar_events(date_str),
            "existing_content":read_file_safe(dp),"vault_changes":scan_vault_changes(vr,date_str),
            "obsidian_sync":sync_obsidian(),"dingtalk_class_msgs":get_dingtalk_class_msgs(date_str)}

def main():
    if len(sys.argv)<2: print("Usage: collect_data.py diary YYYY-MM-DD",file=sys.stderr);sys.exit(1)
    if sys.argv[1]=="diary": print(json.dumps(collect_diary_data(sys.argv[2]),ensure_ascii=False,indent=2))
    elif sys.argv[1]=="weekly": print(json.dumps({"error":"Weekly not implemented"},ensure_ascii=False))

if __name__=="__main__": main()
