#!/usr/bin/env python3
"""个人财务分析 v3.0 — 十段深度分析 + 模板分离HTML
stdlib-only, 零依赖。"""
import csv, sys, io, os
from collections import defaultdict, Counter
from datetime import datetime, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

HELP_TEXT = """个人财务分析工具 v3.0

用法: python3 analyze.py <CSV文件路径> [选项]
选项:
  --html PATH    生成HTML报告
  --detail PATH  导出交易明细JSON（供AI深度分析使用）
  --monthly N    订阅>收入N%告警 (默认5)
  --anomaly N    单笔>月均N%异常 (默认10)
  -h, --help     帮助
"""

COLUMN_ALIASES = {
    'time':['时间','time','日期','date','交易时间'],
    'type':['类型','type','收支类型','方向'],
    'cat':['分类','category','一级分类','大类'],
    'subcat':['二级分类','subcategory','子分类','小类'],
    'amount':['金额','amount','数额','价格'],
    'currency':['币种','currency'],
    'note':['备注','note','说明','描述','remark'],
    'reimbursed':['已报销','reimbursed','报销状态'],
}
WD_NAMES = ['周一','周二','周三','周四','周五','周六','周日']
EAT_CATS = {'吃喝','餐饮','food','吃饭','外卖','食堂'}
TIER_RULES = [
    ({'cat':'住房'},'必要'),({'cat':'房租'},'必要'),({'cat':'话费网费'},'必要'),
    ({'cat':'厨房相关'},'必要'),({'cat':'身体健康'},'必要'),
    ({'cat':'交通','sub':'地铁'},'必要'),({'cat':'吃喝','sub':'每日吃饭'},'必要'),
    ({'cat':'吃喝','sub':'加餐'},'改善'),({'cat':'吃喝','sub':'纯净水'},'改善'),
    ({'cat':'交通','sub':'火车'},'改善'),({'cat':'交通','sub':'打车'},'改善'),
    ({'cat':'家居生活'},'改善'),({'cat':'衣着形象'},'改善'),({'cat':'自我提升'},'改善'),
    ({'cat':'电器'},'欲望'),({'cat':'理财产品'},'欲望'),({'cat':'付费会员'},'欲望'),
    ({'cat':'娱乐'},'欲望'),({'cat':'请客送礼'},'欲望'),
    ({'cat':'吃喝','sub':'大餐'},'欲望'),({'cat':'吃喝','sub':'饮料零食'},'欲望'),
    ({'cat':'其它'},'欲望'),
]

def _f(x): return f"{x:,.2f}"
def _p(a,b): return a/b*100 if b else 0

def tier(e):
    for rule, t in TIER_RULES:
        if rule.get('cat')==e['cat']:
            if 'sub' in rule and rule['sub']!=e['sub']: continue
            return t
    return '改善'

def find_col(headers, *aliases):
    for a in aliases:
        for h in headers:
            if h.strip()==a: return h
    return None

def parse_csv(fp):
    with open(fp, encoding='utf-8-sig') as f:
        rdr = csv.DictReader(f); headers = rdr.fieldnames or []; rows = list(rdr)
    cm = {k:find_col(headers,*v) for k,v in COLUMN_ALIASES.items()}
    missing = [k for k in ['time','amount'] if cm.get(k) is None]
    if missing: print(f"错误: 缺少列 {missing}\n可用: {headers}"); sys.exit(1)
    # 已报销列（可选，不存在则全部视为个人支出）
    reimb_col = cm.get('reimbursed')
    exp, inc, reimburse, reimburse_pending, skipped = [], [], [], [], 0
    for row in rows:
        ts = (row.get(cm['time'],'') or '').strip()
        if not ts: skipped+=1; continue
        try: dt = datetime.strptime(ts[:19],'%Y-%m-%d %H:%M:%S')
        except ValueError:
            try: dt = datetime.strptime(ts[:10],'%Y-%m-%d')
            except ValueError: skipped+=1; continue
        as_ = (row.get(cm['amount'],'') or '').strip().replace(',','')
        try: amt=float(as_)
        except ValueError: skipped+=1; continue
        cat = (row.get(cm.get('cat',''),'') or '未分类').strip()
        sub = (row.get(cm.get('subcat',''),'') or '').strip()
        note = (row.get(cm.get('note',''),'') or '').strip()
        type_val = (row.get(cm.get('type',''),'') or '支出').strip()
        reimbursed_val = (row.get(reimb_col,'') or '').strip() if reimb_col else ''
        e = {'date':dt,'amount':amt,'cat':cat,'sub':sub,'note':note,'type':type_val,'reimbursed':reimbursed_val}
        e['tier'] = tier(e)
        if '收入' in type_val:
            inc.append(e)
        elif '报销记录' in type_val:
            # 报销记录（尚未报销，关联到历史报销条目）
            reimburse_pending.append(e)
        elif '报销' in type_val:
            # 报销类型：根据"已报销"列判断是否已到账
            if reimbursed_val in ('是','已报销','yes','true','1'):
                reimburse.append(e)
            else:
                reimburse_pending.append(e)
        else:
            exp.append(e)
    return exp, inc, reimburse, reimburse_pending, skipped


def compute_analysis(fp, monthly_threshold=5, anomaly_threshold=10):
    exp, inc, reimburse, reimburse_pending, skipped = parse_csv(fp)
    total = len(exp)+len(inc)+len(reimburse)+len(reimburse_pending)
    if total==0: print("错误: 无数据"); sys.exit(1)
    # 报销汇总
    reimb_total = sum(e['amount'] for e in reimburse)
    reimb_pending_total = sum(e['amount'] for e in reimburse_pending)
    all_reimburse = reimburse + reimburse_pending
    TI=sum(e['amount'] for e in inc); TE=sum(e['amount'] for e in exp)
    # 日期范围覆盖所有记录
    all_records = exp + inc + reimburse + reimburse_pending
    dmin=min(e['date'] for e in all_records); dmax=max(e['date'] for e in all_records)
    if not exp and not reimburse and not reimburse_pending: print("错误: 无支出"); sys.exit(1)
    days=max((dmax-dmin).days+1,1)
    active=len(set(e['date'].strftime('%Y-%m-%d') for e in all_records if e.get('amount',0)!=0))
    NET=TI-TE; daily_avg=TE/days if days else 0

    # -- Monthly --
    monthly=defaultdict(lambda:{'exp':0,'inc':0,'cnt':0,'cats':defaultdict(float)})
    for e in exp:
        k=e['date'].strftime('%Y-%m'); monthly[k]['exp']+=e['amount']; monthly[k]['cnt']+=1
        monthly[k]['cats'][e['cat']]+=e['amount']
    for e in inc: monthly[e['date'].strftime('%Y-%m')]['inc']+=e['amount']
    ms=sorted(monthly.keys())

    # -- Category ranking --
    cat_sp=defaultdict(float)
    for e in exp: cat_sp[e['cat']]+=e['amount']
    sorted_cats=sorted(cat_sp.items(),key=lambda x:x[1],reverse=True)

    # -- Sub-category --
    sub_sp=defaultdict(float)
    for e in exp:
        lbl=f"{e['cat']} - {e['sub']}" if e['sub'] else e['cat']
        sub_sp[lbl]+=e['amount']
    sorted_subs=sorted(sub_sp.items(),key=lambda x:x[1],reverse=True)[:15]

    # -- Weekly --
    wd_data=defaultdict(lambda:{'total':0,'cnt':0})
    for e in exp: wd_data[e['date'].weekday()]['total']+=e['amount']; wd_data[e['date'].weekday()]['cnt']+=1

    # -- Subscriptions --
    subs=[e for e in exp if '会员' in e['cat'] or '订阅' in e['cat']]
    sub_grp=defaultdict(lambda:{'total':0,'cnt':0,'entries':[]})
    for e in subs:
        k=e['sub'] or e['cat']; sub_grp[k]['total']+=e['amount']; sub_grp[k]['cnt']+=1; sub_grp[k]['entries'].append(e)

    # -- Anomalies --
    mai=TI/max(len(ms),1); ac=mai*(anomaly_threshold/100)
    anomalies=sorted([e for e in exp if e['amount']>=ac],key=lambda x:x['amount'],reverse=True)

    # -- Top 10 --
    top_exp=sorted(exp,key=lambda x:x['amount'],reverse=True)[:10]

    # ═══ 1. 收支结构全景 ═══
    tier_sp=defaultdict(float)
    for e in exp: tier_sp[e['tier']]+=e['amount']
    essential_in=_p(tier_sp.get('必要',0),TI)
    improve_in=_p(tier_sp.get('改善',0),TI)
    want_in=_p(tier_sp.get('欲望',0),TI)

    # ═══ 2. 收入分析 ═══
    inc_by_cat=defaultdict(float)
    for e in inc: inc_by_cat[e['cat']]+=e['amount']
    incs=[monthly[m]['inc'] for m in ms]
    mean_inc=sum(incs)/len(incs) if incs else 0
    variance=sum((x-mean_inc)**2 for x in incs)/(len(incs)-1) if len(incs)>1 else 0
    cv_inc=(variance**0.5)/mean_inc if mean_inc>0 else 0
    inc_sources_count=len(inc_by_cat)
    if inc_sources_count<=1: diversity_note='单一来源风险'
    elif inc_sources_count>=3: diversity_note='多元化良好'
    else: diversity_note='可增加副业'
    stability_note='稳定' if cv_inc<0.3 else '中等波动' if cv_inc<0.6 else '波动较大'

    # ═══ 3. 支出效率 ═══
    fixed_cats={'住房','话费网费','付费会员'}
    fixed_exp=sum(e['amount'] for e in exp if e['cat'] in fixed_cats)
    variable_exp=TE-fixed_exp
    fixed_inc_rate=_p(fixed_exp/len(ms),TI/len(ms))
    big_items=[e for e in exp if e['amount']>=500]; big_items.sort(key=lambda x:x['amount'],reverse=True)
    big_total=sum(e['amount'] for e in big_items)
    daily_ex_big=(TE-big_total)/days if days else 0

    notes_counter=Counter(e['note'] for e in exp if e['note'] and len(e['note'])>=2)
    recurring={k:v for k,v in notes_counter.items() if v>=3}

    # ═══ 4. 吃喝 ═══
    eat_exp=[e for e in exp if e['cat'] in EAT_CATS]
    eat_total=sum(e['amount'] for e in eat_exp)
    eat_daily=eat_total/days
    engel=_p(eat_total,TE)
    eat_by_sub=defaultdict(lambda:{'total':0,'cnt':0})
    for e in eat_exp: eat_by_sub[e['sub']]['total']+=e['amount']; eat_by_sub[e['sub']]['cnt']+=1
    feast=eat_by_sub.get('大餐',{'total':0,'cnt':0})
    daily_meal=eat_by_sub.get('每日吃饭',{'total':0,'cnt':0})
    eat_insight=''
    if feast['cnt']>0:
        eat_insight+=f'<p style="margin-top:8px;font-size:14px">大餐次均 <strong>¥{feast["total"]/feast["cnt"]:,.2f}</strong>，每 <strong>{days/max(feast["cnt"],1):.0f}</strong> 天一次</p>'
    if daily_meal['cnt']>0:
        avg_m=daily_meal['total']/daily_meal['cnt']
        save_cook=daily_meal['cnt']*max(0,avg_m-15)
        eat_insight+=f'<p style="font-size:14px">日常吃饭次均 <strong>¥{avg_m:,.2f}</strong>，如果自己做(¥15/餐)，可省 <strong>¥{save_cook:,.0f}</strong></p>'

    # ═══ 5. 现金流时序 ═══
    paydays=[e['date'] for e in inc if e['cat']=='工资']
    post_pay=[]
    for pd in paydays:
        for e in exp:
            delta=(e['date']-pd).days
            if 0<=delta<=7: post_pay.append(e['amount'])
    avg_post=sum(post_pay)/len(post_pay) if post_pay else 0
    post_pay_note=''
    if avg_post>daily_avg*1.2: post_pay_note=f' ⚠️ 发薪后消费冲动 (+{(avg_post/daily_avg-1)*100:.0f}%)'
    else: post_pay_note=' — 发薪后未见冲动消费'
    first_half=sum(e['amount'] for e in exp if e['date'].day<=15)
    second_half=sum(e['amount'] for e in exp if e['date'].day>15)

    # ═══ 6. 消费行为画像 ═══
    tod={'晨(6-10点)':0,'午(10-14点)':0,'下午(14-18点)':0,'晚(18-22点)':0,'深夜(22-6点)':0}
    for e in exp:
        h=e['date'].hour
        if 6<=h<10: tod['晨(6-10点)']+=e['amount']
        elif 10<=h<14: tod['午(10-14点)']+=e['amount']
        elif 14<=h<18: tod['下午(14-18点)']+=e['amount']
        elif 18<=h<22: tod['晚(18-22点)']+=e['amount']
        else: tod['深夜(22-6点)']+=e['amount']

    wd_cats=defaultdict(lambda:{'wd':0,'we':0})
    for e in exp:
        if e['date'].weekday()>=5: wd_cats[e['cat']]['we']+=e['amount']
        else: wd_cats[e['cat']]['wd']+=e['amount']

    buckets=[(0,10),(10,30),(30,50),(50,100),(100,500),(500,1000),(1000,999999)]
    dist_data=[]
    for lo,hi in buckets:
        cnt=sum(1 for e in exp if lo<=e['amount']<hi)
        amt=sum(e['amount'] for e in exp if lo<=e['amount']<hi)
        dist_data.append({'lo':lo,'hi':hi,'cnt':cnt,'amt':amt,'pct':_p(cnt,len(exp))})

    # ═══ 7. 理财 ═══
    invest=[e for e in exp if e['cat']=='理财产品']
    invest_total=sum(e['amount'] for e in invest)

    # ═══ 8. 预测 ═══
    last3=ms[-3:] if len(ms)>=3 else ms
    avg_inc_3=sum(monthly[m]['inc'] for m in last3)/len(last3)
    avg_exp_3=sum(monthly[m]['exp'] for m in last3)/len(last3)
    normal_ms=[m for m in ms if monthly[m]['exp']<10000]
    normal_exp_avg=sum(monthly[m]['exp'] for m in normal_ms)/len(normal_ms) if normal_ms else avg_exp_3
    scenario_a_net=avg_inc_3-normal_exp_avg

    # ═══ 9. 省钱潜力 ═══
    savings_items=[]
    daily_eat=[e for e in exp if e['sub']=='每日吃饭']
    if daily_eat:
        avg_me=sum(e['amount'] for e in daily_eat)/len(daily_eat)
        if avg_me>25: savings_items.append(('每日吃饭',f'次均¥{avg_me:,.2f}','¥25/餐',(avg_me-25)*len(daily_eat)/len(ms)))
    feast_list=[e for e in exp if e['sub']=='大餐']
    if len(feast_list)>len(ms)*2:
        current_rate=len(feast_list)/len(ms)
        avg_f=sum(e['amount'] for e in feast_list)/max(len(feast_list),1)
        savings_items.append(('大餐频率',f'{current_rate:.0f}次/月','2次/月',avg_f*(current_rate-2)))
    snacks_t=sum(e['amount'] for e in exp if e['sub']=='饮料零食')
    if snacks_t>200: savings_items.append(('饮料零食',f'总额¥{snacks_t:,.0f}','自备省60%',snacks_t*0.6/len(ms)))
    if subs:
        sm=sum(e['amount'] for e in subs)/len(ms)
        savings_items.append(('订阅精简',f'月均¥{sm:,.0f}','砍30%',sm*0.3))
    ent=sum(e['amount'] for e in exp if e['cat']=='娱乐')
    if ent>0: savings_items.append(('娱乐消费',f'总额¥{ent:,.0f}','砍30%',ent*0.3/len(ms)))
    total_monthly_save=sum(s[-1] for s in savings_items)
    orig_rate=_p(NET/len(ms),avg_inc_3) if avg_inc_3>0 else 0
    opt_rate=_p(NET/len(ms)+total_monthly_save,avg_inc_3) if avg_inc_3>0 else 0

    # ═══ 10. 指标仪表盘 ═══
    consistency=active/days*100
    want_rate=_p(tier_sp.get('欲望',0),TE)
    indicators=[]
    def ind(name,val,target,ok):
        indicators.append({'name':name,'value':val,'target':target,'ok':ok})
    ind('结余率',f'{_p(NET,TI) if TI>0 else 0:.1f}%','≥30%',_p(NET,TI)>=30 if TI>0 else False)
    ind('固定支出/收入',f'{fixed_inc_rate:.1f}%','≤50%',fixed_inc_rate<=50)
    ind('恩格尔系数',f'{engel:.1f}%','30-40%',30<=engel<=40)
    ind('欲望占比',f'{want_rate:.1f}%','≤30%',want_rate<=30)
    ind('记账坚持度',f'{consistency:.1f}%','≥90%',consistency>=90)
    ind('必要/收入',f'{essential_in:.1f}%','≤50%',essential_in<=50)
    ind('收入稳定性',f'{cv_inc:.2f}','<0.3',cv_inc<0.3)
    passed_count=sum(1 for x in indicators if x['ok'])

    # -- Health score --
    score=0; sd={}
    if TI>0:
        sr=NET/TI; score+=max(0,min(30,30-(0.30-sr)*100))
        sd['savings']={'score':max(0,min(30,30-(0.30-sr)*100)),'value':f'{sr*100:.1f}%'}
        er=tier_sp.get('必要',0)/TI; score+=max(0,min(25,25-(er-0.50)*100))
        sd['essential']={'score':max(0,min(25,25-(er-0.50)*100)),'value':f'{er*100:.1f}%'}
    else: sd['savings']=sd['essential']={'score':0,'value':'N/A'}
    wr=want_rate/100; score+=max(0,min(25,25-(wr-0.30)*100))
    sd['want']={'score':max(0,min(25,25-(wr-0.30)*100)),'value':f'{want_rate:.1f}%'}
    cr=consistency/100; score+=max(0,min(20,20-(0.90-cr)*100))
    sd['consistency']={'score':max(0,min(20,20-(0.90-cr)*100)),'value':f'{consistency:.1f}%'}
    score=round(score)
    if score>=85: grade='优秀'
    elif score>=70: grade='良好'
    elif score>=50: grade='一般'
    else: grade='预警'

    return {
        'fp':fp,'total':total,'skipped':skipped,
        'dmin':dmin,'dmax':dmax,'days':days,'active':active,
        'TI':TI,'TE':TE,'NET':NET,'daily_avg':daily_avg,
        'sorted_cats':sorted_cats,'sorted_subs':sorted_subs,
        'monthly':monthly,'ms':ms,
        'wd_data':wd_data,'top_exp':top_exp,
        'subs':subs,'sub_grp':sub_grp,'anomalies':anomalies,'ac':ac,
        'tier_sp':tier_sp,'essential_in':essential_in,'improve_in':improve_in,'want_in':want_in,
        'inc_by_cat':inc_by_cat,'cv_inc':cv_inc,'diversity_note':diversity_note,'stability_note':stability_note,
        'inc_sources_count':inc_sources_count,'mean_inc':mean_inc,
        'fixed_exp':fixed_exp,'variable_exp':variable_exp,'fixed_inc_rate':fixed_inc_rate,
        'big_items':big_items,'big_total':big_total,'daily_ex_big':daily_ex_big,
        'recurring':recurring,
        'eat_total':eat_total,'eat_daily':eat_daily,'engel':engel,'eat_by_sub':eat_by_sub,
        'feast':feast,'daily_meal':daily_meal,
        'paydays':paydays,'avg_post':avg_post,'post_pay_note':post_pay_note,
        'first_half':first_half,'second_half':second_half,
        'tod':tod,'wd_cats':wd_cats,'dist_data':dist_data,
        'invest':invest,'invest_total':invest_total,
        'avg_inc_3':avg_inc_3,'avg_exp_3':avg_exp_3,
        'normal_exp_avg':normal_exp_avg,'scenario_a_net':scenario_a_net,
        'savings_items':savings_items,'total_monthly_save':total_monthly_save,
        'orig_rate':orig_rate,'opt_rate':opt_rate,
        'indicators':indicators,'passed_count':passed_count,
        'score':score,'grade':grade,'sd':sd,
        'monthly_threshold':monthly_threshold,'anomaly_threshold':anomaly_threshold,
        'eat_insight':eat_insight,
        'inc': inc,
        'reimburse': reimburse, 'reimburse_pending': reimburse_pending,
        'reimb_total': reimb_total, 'reimb_pending_total': reimb_pending_total,
        'all_reimburse': all_reimburse,
        'big_pct': _p(big_total, TE),
    }


# ═══════════ Terminal Output ═══════════
def sep(t): print(f"\n{'='*56}\n  {t}\n{'='*56}")

def print_report(d):
    print(f"\n总记录: {d['total']} 条"+ (f" (跳过{d['skipped']}条)" if d['skipped'] else ""))
    print(f"数据范围: {d['dmin'].strftime('%Y-%m-%d')} ~ {d['dmax'].strftime('%Y-%m-%d')}  ({d['days']}天, 记账{d['active']}天)")
    print(f"\n  总收入:  {_f(d['TI']):>12}")
    print(f"  总支出:  {_f(d['TE']):>12}")
    print(f"  净结余:  {_f(d['NET']):>12}")
    if d['TI']>0:
        r=d['NET']/d['TI']*100; lb='储蓄率' if d['NET']>=0 else '赤字率'
        print(f"  {lb}:  {abs(r):>11.1f}%")
    print(f"  日均支出: {d['daily_avg']:>10,.2f}")
    if d['reimb_pending_total'] > 0:
        print(f"  待报销:  {_f(d['reimb_pending_total']):>12}  ⚠️ 公司未打款（不计入个人消费）")
    print(f"  健康评分: {d['score']:>11} / 100  ({d['grade']})")

    sep("一、收支结构全景")
    for t in ['必要','改善','欲望']:
        amt=d['tier_sp'].get(t,0); pct=_p(amt,d['TE'])
        print(f"  {t}: {_f(amt):>12}  ({pct:5.1f}%)  {'#'*int(pct)}")
    print(f"\n  50/30/20: 必要 {d['essential_in']:.1f}% | 改善 {d['improve_in']:.1f}% | 欲望 {d['want_in']:.1f}%")

    sep("二、收入深度分析")
    print(f"  月均收入: {_f(d['mean_inc'])}  最高: {max(d['monthly'].values(),key=lambda x:x['inc'])['inc']:.0f}  最低: {min(d['monthly'].values(),key=lambda x:x['inc'])['inc']:.0f}")
    print(f"  变异系数: {d['cv_inc']:.2f} ({d['stability_note']})  来源数: {d['inc_sources_count']} ({d['diversity_note']})")
    for cat,amt in sorted(d['inc_by_cat'].items(),key=lambda x:x[1],reverse=True):
        print(f"    {cat:<10} {_f(amt):>10}  ({_p(amt,d['TI']):.1f}%)")

    sep("三、支出效率分析")
    print(f"  固定: {_f(d['fixed_exp'])} ({_p(d['fixed_exp'],d['TE']):.1f}%)  可变: {_f(d['variable_exp'])} ({_p(d['variable_exp'],d['TE']):.1f}%)")
    print(f"  固定/收入: {d['fixed_inc_rate']:.1f}%")
    print(f"  大额(>=500): {len(d['big_items'])}笔 共{_f(d['big_total'])}  剔除后日均: {_f(d['daily_ex_big'])}")
    if d['recurring']:
        print(f"  周期性消费:")
        for note,cnt in sorted(d['recurring'].items(),key=lambda x:x[1],reverse=True)[:5]:
            ttl=sum(e['amount'] for e in d['subs']+d['big_items'] if e['note']==note) or sum(e['amount'] for e in [] if 0)
            print(f"    '{note}' x{cnt}次")

    sep("四、吃喝行为深度拆解")
    print(f"  总计: {_f(d['eat_total'])}  日均: {_f(d['eat_daily'])}  恩格尔系数: {d['engel']:.1f}%")
    for sub,dd in sorted(d['eat_by_sub'].items(),key=lambda x:x[1]['total'],reverse=True):
        avg=dd['total']/dd['cnt'] if dd['cnt'] else 0
        print(f"    {sub:<12} {_f(dd['total']):>10}  ({dd['cnt']:>3}次)  次均{_f(avg)}")

    sep("五、现金流时序分析")
    if d['paydays']:
        print(f"  发薪日: {', '.join(p.strftime('%m/%d') for p in d['paydays'])}")
        print(f"  发薪后7天日均: {_f(d['avg_post'])}  全局: {_f(d['daily_avg'])}{d['post_pay_note']}")
    print(f"  上半月: {_f(d['first_half'])} ({_p(d['first_half'],d['TE']):.0f}%)  下半月: {_f(d['second_half'])} ({_p(d['second_half'],d['TE']):.0f}%)")

    sep("六、消费行为画像")
    print("  消费时段:")
    for tl,amt in d['tod'].items():
        print(f"    {tl}: {_f(amt):>10} ({_p(amt,d['TE']):5.1f}%) {'#'*int(_p(amt,d['TE'])/3)}")
    print("  金额分布:")
    for dd in d['dist_data']:
        print(f"    {dd['lo']:>4}-{dd['hi']:<6} {dd['cnt']:>4}笔 ({dd['pct']:5.1f}%)  {_f(dd['amt']):>10}")

    sep("七、理财与资产")
    if d['invest']:
        print(f"  理财类支出: {_f(d['invest_total'])} ({len(d['invest'])}笔)")
        print(f"  注: 理财是资产转换，剔除后实际消费 {_f(d['TE']-d['invest_total'])}")
        for e in d['invest']:
            print(f"    {e['date'].strftime('%m-%d')}  {e['note']:<15} {_f(e['amount']):>10}")
    else: print("  无理财记录")

    # 报销追踪（钱迹"报销"/"报销记录"类型）
    if d['reimburse'] or d['reimburse_pending']:
        sep("报销追踪（公司垫付）")
        print(f"  已报销（已到账）: {_f(d['reimb_total'])} ({len(d['reimburse'])}笔)")
        print(f"  待报销（未到账）: {_f(d['reimb_pending_total'])} ({len(d['reimburse_pending'])}笔)")
        print(f"  注: 以上为公司报销款项，不计入个人消费。待报销的 {_f(d['reimb_pending_total'])} 应尽快提交报销单")
        if d['reimburse']:
            print(f"\n  [已报销明细]")
            for e in sorted(d['reimburse'], key=lambda x: x['date']):
                det = f"{e['cat']}/{e['sub']}" if e['sub'] else e['cat']
                print(f"    {e['date'].strftime('%m-%d')}  {det:<22} {_f(e['amount']):>10}  {e['note']}  ✅已到账")
        if d['reimburse_pending']:
            print(f"\n  [待报销明细] ⚠️ 公司尚未打款")
            for e in sorted(d['reimburse_pending'], key=lambda x: x['date']):
                det = f"{e['cat']}/{e['sub']}" if e['sub'] else e['cat']
                print(f"    {e['date'].strftime('%m-%d')}  {det:<22} {_f(e['amount']):>10}  {e['note']}  🔴待报销")

    sep("八、未来预测")
    print(f"  近3月月均收入: {_f(d['avg_inc_3'])}  支出: {_f(d['avg_exp_3'])}")
    print(f"  情境A(正常月): 月结余 {_f(d['scenario_a_net'])}")
    print(f"  情境B(含大额): 月结余 {_f(d['avg_inc_3']-d['avg_exp_3'])}")
    for i in range(1,4):
        nm=(d['dmax']+timedelta(days=30*i)).strftime('%Y-%m')
        cum=d['NET']+d['scenario_a_net']*i
        print(f"  预测 {nm}: 累计净资产~{_f(cum)}")

    sep("九、省钱潜力")
    for item,cur,target,sv in d['savings_items']:
        print(f"  {item:<14} {cur:<20} -> {target:<12} 月省 {_f(sv):>10}")
    print(f"  合计月省: {_f(d['total_monthly_save'])}  年化: {_f(d['total_monthly_save']*12)}")

    sep("十、关键指标仪表盘")
    for ind in d['indicators']:
        st='PASS' if ind['ok'] else 'FAIL'
        print(f"  [{st}] {ind['name']:<18} {ind['value']:>8}  目标: {ind['target']}")
    print(f"  达标: {d['passed_count']}/{len(d['indicators'])}")

    sep("附录: 支出分类排行")
    for i,(cat,amt) in enumerate(d['sorted_cats'],1):
        pct=_p(amt,d['TE']); print(f"  {i:2}. {cat:<12} {_f(amt):>12}  ({pct:5.1f}%)  {'#'*int(pct)}")

    sep("附录: 月度趋势")
    print(f"  {'月份':<8} {'收入':>10} {'支出':>10} {'结余':>10} {'储蓄率':>7}  {'笔数':>5}")
    print("  "+"-"*52)
    for m in d['ms']:
        md=d['monthly'][m]; nm=md['inc']-md['exp']
        rm=(nm/md['inc']*100) if md['inc']>0 else float('-inf')
        rs=f"{rm:6.1f}%" if rm!=float('-inf') else "   N/A"
        print(f"  {m:<8} {_f(md['inc']):>10} {_f(md['exp']):>10} {_f(nm):>10} {rs:>7}  {md['cnt']:>5}")

    sep("附录: 单笔最高 TOP 10")
    for i,e in enumerate(d['top_exp'],1):
        det=f"{e['cat']}/{e['sub']}" if e['sub'] else e['cat']
        print(f"  {i:2}. {e['date'].strftime('%m-%d')}  {det:<22} {_f(e['amount']):>12}  {e['note']}")

    if d['subs']:
        sep("附录: 订阅追踪")
        st=sum(e['amount'] for e in d['subs'])
        print(f"  总计: {_f(st)} ({len(d['subs'])}笔, 月均 {_f(st/max(len(d['ms']),1))})")
        for name,data in sorted(d['sub_grp'].items(),key=lambda x:x[1]['total'],reverse=True):
            print(f"  [{name}] {_f(data['total'])} | {data['cnt']}笔")
            for e in data['entries']:
                print(f"    {e['date'].strftime('%m-%d')}  {_f(e['amount']):>10}  {e['note']}")

    if d['anomalies']:
        sep("附录: 异常大额")
        for e in d['anomalies']:
            print(f"  !! {e['date'].strftime('%Y-%m-%d')}  {e['cat']}/{e['sub']}  {_f(e['amount']):>12}  {e['note']}")

    print(f"\n{'='*56}\n  报告结束\n{'='*56}")


# ═══════════════ HTML Template Engine ═══════════════
_BAR_COLORS=['#667eea','#764ba2','#f093fb','#f5576c','#fdbb2d','#ff6b6b','#48dbfb','#ff9ff3','#54a0ff','#5f27cd',
             '#01a3a4','#6ab04c','#e056a0','#c44569','#3dc1d3']

def _bc(i): return _BAR_COLORS[i%len(_BAR_COLORS)]
def _tc(t): return {'必要':'#3498db','改善':'#f39c12','欲望':'#e74c3c'}.get(t,'#888')
def _sc(s): return '#2ecc71' if s>=85 else '#3498db' if s>=70 else '#f39c12' if s>=50 else '#e74c3c'

def _load_tmpl():
    sd=os.path.dirname(os.path.abspath(__file__))
    tp=os.path.join(sd,'template.html')
    if not os.path.exists(tp): print(f"错误: 模板不存在 {tp}"); sys.exit(1)
    with open(tp,encoding='utf-8') as f: return f.read()

def _build_bar(items, total, bar_min=90, lbl_min=160, sz=''):
    """Build bar chart rows for HTML."""
    html=''
    for i,(lbl,amt) in enumerate(items):
        pct=_p(amt,total)
        ls=f'style="min-width:{lbl_min}px;font-size:13px"' if lbl_min>90 else ''
        html+=f'<div class="bar-item"><span class="bar-label" {ls}>{lbl}</span><span class="bar-track"><span class="bar-fill" style="width:{pct:.1f}%;background:{_bc(i)}"></span></span><span class="bar-val">{_f(amt)}</span><span class="bar-pct">{pct:.1f}%</span></div>'
    return html

def generate_html(d, output_path):
    t=_load_tmpl()

    # Overview cards
    if d['TI']>0:
        r=d['NET']/d['TI']*100; stag='<span class="tag tag-green">有结余</span>' if d['NET']>=0 else '<span class="tag tag-red">赤字中</span>'
        rate_s=f"{abs(r):.1f}%"
    else: stag=''; rate_s='N/A'
    nc='pos' if d['NET']>=0 else 'neg'

    t=t.replace('{{FILENAME}}',os.path.basename(d['fp']))
    t=t.replace('{{DATE_RANGE}}',f"{d['dmin'].strftime('%Y-%m-%d')} ~ {d['dmax'].strftime('%Y-%m-%d')}")
    t=t.replace('{{DAYS}}',str(d['days'])); t=t.replace('{{ACTIVE_DAYS}}',str(d['active']))
    t=t.replace('{{TOTAL_ROWS}}',str(d['total']))
    t=t.replace('{{INCOME_CARD}}',_f(d['TI'])); t=t.replace('{{EXPENSE_CARD}}',_f(d['TE']))
    t=t.replace('{{STATUS_TAG}}',stag); t=t.replace('{{NET_CLASS}}',nc)
    t=t.replace('{{NET_CARD}}',_f(d['NET']))
    t=t.replace('{{SCORE_COLOR}}',_sc(d['score'])); t=t.replace('{{SCORE}}',str(d['score']))

    # 1. Structure
    tc='';
    for tier in ['必要','改善','欲望']:
        amt=d['tier_sp'].get(tier,0); pct=_p(amt,d['TE'])
        tc+=f'<div class="tier-card"><div class="t-name">{tier}</div><div class="t-amt" style="color:{_tc(tier)}">{_f(amt)}</div><div class="t-pct">{pct:.1f}%</div></div>'
    t=t.replace('{{TIER_CARDS}}',tc)
    t=t.replace('{{ESSENTIAL_PCT}}',f"{d['essential_in']:.1f}")
    t=t.replace('{{IMPROVE_PCT}}',f"{d['improve_in']:.1f}")
    t=t.replace('{{WANT_PCT}}',f"{d['want_in']:.1f}")

    # 2. Income
    t=t.replace('{{AVG_MONTHLY_INC}}',_f(d['mean_inc']))
    t=t.replace('{{MAX_MONTH_INC}}',f"{max(d['monthly'].values(),key=lambda x:x['inc'])['inc']:.0f}")
    t=t.replace('{{MIN_MONTH_INC}}',f"{min(d['monthly'].values(),key=lambda x:x['inc'])['inc']:.0f}")
    inc_srcs=' · '.join(f"{cat} {_f(amt)} ({_p(amt,d['TI']):.0f}%)" for cat,amt in sorted(d['inc_by_cat'].items(),key=lambda x:x[1],reverse=True))
    t=t.replace('{{INC_SOURCES}}',inc_srcs)
    t=t.replace('{{INC_CV}}',f"{d['cv_inc']:.2f}"); t=t.replace('{{INC_STABILITY}}',d['stability_note'])
    t=t.replace('{{INC_SOURCE_COUNT}}',str(d['inc_sources_count'])); t=t.replace('{{INC_DIVERSITY}}',d['diversity_note'])

    # 3. Efficiency
    t=t.replace('{{FIXED_EXP}}',_f(d['fixed_exp'])); t=t.replace('{{FIXED_PCT}}',f"{_p(d['fixed_exp'],d['TE']):.1f}")
    t=t.replace('{{VARIABLE_EXP}}',_f(d['variable_exp'])); t=t.replace('{{VARIABLE_PCT}}',f"{_p(d['variable_exp'],d['TE']):.1f}")
    t=t.replace('{{FIXED_INC_RATE}}',f"{d['fixed_inc_rate']:.1f}")
    t=t.replace('{{BIG_COUNT}}',str(len(d['big_items']))); t=t.replace('{{BIG_TOTAL}}',_f(d['big_total']))
    t=t.replace('{{BIG_PCT}}',f"{_p(d['big_total'],d['TE']):.1f}")
    t=t.replace('{{DAILY_EX_BIG}}',_f(d['daily_ex_big']))
    if d['recurring']:
        rec_html='<p style="margin-top:12px;font-weight:700">疑似周期性消费</p><table><thead><tr><th>备注</th><th style="text-align:center">次数</th></tr></thead><tbody>'
        for note,cnt in sorted(d['recurring'].items(),key=lambda x:x[1],reverse=True)[:5]:
            rec_html+=f'<tr><td>{note}</td><td style="text-align:center">{cnt}</td></tr>'
        rec_html+='</tbody></table>'
        t=t.replace('{{RECURRING_SECTION}}',rec_html)
    else: t=t.replace('{{RECURRING_SECTION}}','')

    # 4. Dining
    t=t.replace('{{EAT_TOTAL}}',_f(d['eat_total'])); t=t.replace('{{EAT_DAILY}}',_f(d['eat_daily']))
    t=t.replace('{{ENGEL}}',f"{d['engel']:.1f}")
    er='';
    for sub,dd in sorted(d['eat_by_sub'].items(),key=lambda x:x[1]['total'],reverse=True):
        avg=dd['total']/dd['cnt'] if dd['cnt'] else 0
        er+=f'<tr><td>{sub}</td><td style="text-align:right">{_f(dd["total"])}</td><td style="text-align:center">{dd["cnt"]}</td><td style="text-align:right">{_f(avg)}</td><td style="text-align:right">{_f(dd["total"]/d["days"])}</td></tr>'
    t=t.replace('{{EAT_ROWS}}',er); t=t.replace('{{EAT_INSIGHT}}',d['eat_insight'])

    # 5. Cash flow
    t=t.replace('{{PAYDAYS}}',', '.join(p.strftime('%m月%d日') for p in d['paydays']) if d['paydays'] else '未识别')
    t=t.replace('{{POST_PAY_DAILY}}',_f(d['avg_post'])); t=t.replace('{{GLOBAL_DAILY}}',_f(d['daily_avg']))
    t=t.replace('{{POST_PAY_NOTE}}',d['post_pay_note'])
    t=t.replace('{{FIRST_HALF}}',_f(d['first_half'])); t=t.replace('{{FIRST_HALF_PCT}}',f"{_p(d['first_half'],d['TE']):.0f}")
    t=t.replace('{{SECOND_HALF}}',_f(d['second_half'])); t=t.replace('{{SECOND_HALF_PCT}}',f"{_p(d['second_half'],d['TE']):.0f}")

    # 6. Behavior
    tod_html=''
    for tl,amt in d['tod'].items():
        p=_p(amt,d['TE']); tod_html+=f'<div class="bar-item"><span class="bar-label">{tl}</span><span class="bar-track"><span class="bar-fill" style="width:{p:.1f}%;background:#667eea"></span></span><span class="bar-val">{_f(amt)}</span><span class="bar-pct">{p:.1f}%</span></div>'
    t=t.replace('{{TOD_BARS}}',tod_html)
    wwr=''
    for cat,dd in sorted(d['wd_cats'].items(),key=lambda x:x[1]['wd']+x[1]['we'],reverse=True)[:7]:
        total=dd['wd']+dd['we']; we_p=_p(dd['we'],total) if total else 0
        ft='周末型 ⚠️' if we_p>40 else '工作日型'
        wwr+=f'<tr><td>{cat}</td><td style="text-align:center">{we_p:.0f}%</td><td>{ft}</td></tr>'
    t=t.replace('{{WD_WE_ROWS}}',wwr)
    adr=''
    for dd in d['dist_data']:
        adr+=f'<tr><td>¥{dd["lo"]}-{dd["hi"]}</td><td style="text-align:center">{dd["cnt"]} ({dd["pct"]:.1f}%)</td><td style="text-align:right">{_f(dd["amt"])}</td></tr>'
    t=t.replace('{{AMT_DIST_ROWS}}',adr)

    # 7. Investment
    if d['invest']:
        iv=f'<p>理财类支出 <strong>{_f(d["invest_total"])}</strong> ({len(d["invest"])}笔)</p>'
        iv+=f'<p style="font-size:14px;color:var(--muted);margin-top:4px">注: 理财是资产转换非消耗，剔除后实际消费 <strong>{_f(d["TE"]-d["invest_total"])}</strong></p>'
        iv+='<table style="margin-top:12px"><thead><tr><th>日期</th><th>备注</th><th style="text-align:right">金额</th></tr></thead><tbody>'
        for e in d['invest']:
            iv+=f'<tr><td>{e["date"].strftime("%m-%d")}</td><td>{e["note"]}</td><td style="text-align:right">{_f(e["amount"])}</td></tr>'
        iv+='</tbody></table>'
    else: iv='<p>无理财记录</p>'
    t=t.replace('{{INVEST_CONTENT}}',iv)

    # 8. Projection
    t=t.replace('{{RECENT_INC}}',_f(d['avg_inc_3'])); t=t.replace('{{RECENT_EXP}}',_f(d['avg_exp_3']))
    t=t.replace('{{SCENARIO_A_EXP}}',_f(d['normal_exp_avg']))
    t=t.replace('{{SCENARIO_A_NET}}',_f(d['scenario_a_net']))
    t=t.replace('{{SCENARIO_B_EXP}}',_f(d['avg_exp_3']))
    sb_net=d['avg_inc_3']-d['avg_exp_3']
    t=t.replace('{{SCENARIO_B_NET}}',_f(sb_net))
    t=t.replace('{{SCENARIO_B_CLASS}}','net-pos' if sb_net>=0 else 'net-neg')
    pr=''
    for i in range(1,4):
        nm=(d['dmax']+timedelta(days=30*i)).strftime('%Y-%m')
        cum=d['NET']+d['scenario_a_net']*i
        pr+=f'<div class="r-row"><span>{nm}</span><span>累计净资产 ~{_f(cum)}</span></div>'
    t=t.replace('{{PROJECTION_ROWS}}',pr)

    # 9. Savings
    sr=''
    for item,cur,target,sv in d['savings_items']:
        sr+=f'<tr><td>{item}</td><td>{cur}</td><td>{target}</td><td style="text-align:right;color:var(--green);font-weight:600">¥{_f(sv)}</td></tr>'
    t=t.replace('{{SAVINGS_ROWS}}',sr)
    t=t.replace('{{TOTAL_MONTHLY_SAVE}}',_f(d['total_monthly_save']))
    t=t.replace('{{TOTAL_YEARLY_SAVE}}',_f(d['total_monthly_save']*12))
    t=t.replace('{{OPTIMIZED_RATE}}',f"{d['opt_rate']:.1f}")
    t=t.replace('{{ORIGINAL_RATE}}',f"{d['orig_rate']:.1f}")

    # 10. Indicators
    idr=''
    for ind in d['indicators']:
        dot='ok' if ind['ok'] else 'fail'; st='PASS' if ind['ok'] else 'FAIL'
        idr+=f'<tr><td><span class="pass-dot {dot}"></span>{ind["name"]}</td><td style="text-align:right">{ind["value"]}</td><td style="text-align:right">{ind["target"]}</td><td style="text-align:center"><span class="tag {"tag-green" if ind["ok"] else "tag-red"}">{st}</span></td></tr>'
    t=t.replace('{{INDICATOR_ROWS}}',idr)
    t=t.replace('{{PASSED_COUNT}}',str(d['passed_count']))
    t=t.replace('{{TOTAL_INDICATORS}}',str(len(d['indicators'])))

    # Summary
    first_big_note=d['big_items'][0]['note'] if d['big_items'] else '大额消费'
    core_issues=f'1. 大额消费({len(d["big_items"])}笔≥¥500, 占{d["big_pct"]:.1f}%)是赤字主因; 2. 订阅月均负担; 3. 吃喝持续消耗'
    strengths='1. 收入稳定; 2. 记账习惯好; 3. 固定支出控制在线'
    summary=f'''
    <p><strong>核心问题：</strong>{core_issues}</p>
    <p style="margin-top:8px"><strong>核心优势：</strong>{strengths}</p>
    <p style="margin-top:12px;padding:12px;background:#fff;border-radius:8px;border-left:4px solid var(--accent)">
      <strong>一句话：</strong>去掉{first_big_note}等大额消费，你日常月结余约{_f(d['scenario_a_net'])}。
      问题不是赚不够，是大额消费缺乏缓冲。建议设立"大额消费缓冲金"——每月自动转¥1,500到独立账户，大额从这出。
    </p>'''
    t=t.replace('{{SUMMARY_CONTENT}}',summary)

    # Appendix: category
    t=t.replace('{{CAT_BARS}}',_build_bar(d['sorted_cats'],d['TE']))
    t=t.replace('{{SUBCAT_BARS}}',_build_bar(d['sorted_subs'],d['TE'],lbl_min=160))

    # Monthly rows
    mr=''
    for m in d['ms']:
        md=d['monthly'][m]; nm=md['inc']-md['exp']
        rm=(nm/md['inc']*100) if md['inc']>0 else float('-inf')
        nc2='net-pos' if nm>=0 else 'net-neg'
        mr+=f'<tr><td>{m}</td><td style="text-align:right">{_f(md["inc"])}</td><td style="text-align:right">{_f(md["exp"])}</td><td style="text-align:right" class="{nc2}">{_f(nm)}</td><td style="text-align:right">{(f"{rm:.1f}%") if rm!=float("-inf") else "N/A"}</td><td style="text-align:center">{md["cnt"]}</td></tr>'
    t=t.replace('{{MONTHLY_ROWS}}',mr)

    # Top 10
    tr=''
    for i,e in enumerate(d['top_exp'],1):
        det=f"{e['cat']}/{e['sub']}" if e['sub'] else e['cat']
        tr+=f'<tr><td>{i}</td><td>{e["date"].strftime("%m-%d")}</td><td>{det}</td><td style="text-align:right;font-weight:600">{_f(e["amount"])}</td><td style="color:var(--muted);font-size:13px">{e["note"]}</td></tr>'
    t=t.replace('{{TOP_ROWS}}',tr)

    # Subs
    if d['subs']:
        st=sum(e['amount'] for e in d['subs'])
        sh=f'<p style="margin-bottom:16px">订阅总计: <strong>{_f(st)}</strong> ({len(d["subs"])}笔, 月均 <strong>{_f(st/max(len(d["ms"]),1))}</strong>)</p>'
        for name,data in sorted(d['sub_grp'].items(),key=lambda x:x[1]['total'],reverse=True):
            ents=''.join(f'<span class="sg-item"><span>{e["date"].strftime("%m-%d")}</span><span>{_f(e["amount"])}</span><span>{e["note"]}</span></span>' for e in data['entries'])
            sh+=f'<div class="sub-group"><div class="sg-header"><span class="sg-name">{name}</span><span class="sg-stat">合计 {_f(data["total"])} | {data["cnt"]}笔 | 月均 {_f(data["total"]/max(len(d["ms"]),1))}</span></div>{ents}</div>'
        t=t.replace('{{SUBS_SECTION}}',f'<div class="section"><h2>附录：订阅 & 会员追踪</h2>{sh}</div>')
    else: t=t.replace('{{SUBS_SECTION}}','')

    # Income rows
    ir=''.join(f'<tr><td>{e["date"].strftime("%Y-%m-%d")}</td><td>{e["cat"]}</td><td style="text-align:right;color:var(--green);font-weight:600">+{_f(e["amount"])}</td><td style="color:var(--muted);font-size:13px">{e["note"]}</td></tr>' for e in d['inc'])
    t=t.replace('{{INCOME_ROWS}}',ir)

    # Anomalies
    if d['anomalies']:
        ah=f'<p style="font-size:13px;color:var(--muted);margin-bottom:12px">阈值: 单笔 &gt; 月均收入 {d["anomaly_threshold"]}% = {_f(d["ac"])}</p>'
        ah+=''.join(f'<div class="anomaly-item"><span class="anomaly-badge">!!</span><span style="min-width:90px">{e["date"].strftime("%Y-%m-%d")}</span><span>{e["cat"]}/{e["sub"]}</span><span style="flex:1;text-align:right;font-weight:700;color:var(--red)">{_f(e["amount"])}</span><span style="color:var(--muted);font-size:13px">{e["note"]}</span></div>' for e in d['anomalies'])
        t=t.replace('{{ANOMALY_SECTION}}',f'<div class="section" style="border-left:4px solid var(--red)"><h2>附录：异常大额支出</h2>{ah}</div>')
    else: t=t.replace('{{ANOMALY_SECTION}}','')

    t=t.replace('{{GEN_TIME}}',datetime.now().strftime('%Y-%m-%d %H:%M'))

    with open(output_path,'w',encoding='utf-8') as f: f.write(t)
    print(f"\n[HTML] 报告已生成: {output_path}")


def generate_detail_json(d, output_path):
    """导出交易明细JSON，供AI深度分析使用。"""
    import json
    def fmt(e):
        return {
            'date': e['date'].strftime('%Y-%m-%d %H:%M:%S'),
            'amount': e['amount'],
            'cat': e['cat'],
            'sub': e['sub'],
            'note': e['note'],
            'type': e.get('type','支出'),
            'reimbursed': e.get('reimbursed',''),
            'tier': e['tier']
        }
    export = {
        'meta': {
            'file': d['fp'],
            'date_range': f"{d['dmin'].strftime('%Y-%m-%d')} ~ {d['dmax'].strftime('%Y-%m-%d')}",
            'days': d['days'],
            'active_days': d['active'],
            'total_records': d['total'],
            'total_income': round(d['TI'], 2),
            'total_expense': round(d['TE'], 2),
            'net': round(d['NET'], 2),
            'daily_avg': round(d['daily_avg'], 2),
            'health_score': d['score'],
            'health_grade': d['grade'],
            'monthly_threshold': d['monthly_threshold'],
            'anomaly_threshold': d['anomaly_threshold'],
        },
        'expenses': [fmt(e) for e in sorted(d['top_exp'], key=lambda x: x['amount'], reverse=True)
                      + [e for e in sorted(d['subs'], key=lambda x: x['amount'], reverse=True)]
                      + [e for e in sorted(d['anomalies'], key=lambda x: x['amount'], reverse=True)]],
        'income': [{'date': e['date'].strftime('%Y-%m-%d %H:%M:%S'),
                     'amount': e['amount'], 'cat': e['cat'], 'note': e['note']}
                    for e in sorted(d['inc'], key=lambda x: x['date'])],
        'reimburse': [fmt(e) for e in sorted(d['all_reimburse'], key=lambda x: x['date'])],
        'reimburse_total': round(d['reimb_total'], 2),
        'reimburse_pending_total': round(d['reimb_pending_total'], 2),
        'invest_total': round(d['invest_total'], 2),
        'subscriptions': [{'name': name, 'total': round(data['total'], 2), 'count': data['cnt']}
                          for name, data in sorted(d['sub_grp'].items(), key=lambda x: x[1]['total'], reverse=True)],
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export, f, ensure_ascii=False, indent=2)
    print(f"\n[JSON] 交易明细已导出: {output_path}")


# ═══════════════ Main ═══════════════
if __name__=='__main__':
    args=sys.argv[1:]
    if not args or '-h' in args or '--help' in args: print(HELP_TEXT); sys.exit(0)
    fp=args[0]; mt=5; at=10; html_path=None; detail_path=None
    i=1
    while i<len(args):
        if args[i]=='--monthly' and i+1<len(args): mt=float(args[i+1]); i+=2
        elif args[i]=='--anomaly' and i+1<len(args): at=float(args[i+1]); i+=2
        elif args[i]=='--html' and i+1<len(args): html_path=args[i+1]; i+=2
        elif args[i]=='--detail' and i+1<len(args): detail_path=args[i+1]; i+=2
        else: i+=1
    d=compute_analysis(fp,mt,at)
    print_report(d)
    if html_path: generate_html(d,html_path)
    if detail_path: generate_detail_json(d,detail_path)
