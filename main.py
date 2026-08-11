import csv
import os
from DrissionPage import Chromium,ChromiumOptions
from datetime import datetime
"""变量区"""""""""""""""""""""""""""""""""""""""""""""
input_data=[]
# 浏览器端口
tabPort=5563
# 浏览器对象
co = ChromiumOptions()
co.set_local_port(tabPort)
# co.no_imgs(True)
# co.set_load_mode('eager')
dp=Chromium(addr_or_opts=co)
# 标签页对象
tab=dp.get_tab()
# tab.ele("@class=asdf",timeout=0.1).click()
# CSV文件路径
csv_file = 'comments_data.csv'
# 使用后标识
syTemp='background-image: url(&quot;https://img12.360buyimg.com/imagetools/jfs/t1/230854/32/13832/17553/65dc2da8F281458bd/7011f6409622c0a5.png&quot;);'
xj={
    "https://img11.360buyimg.com/img/jfs/t1/265336/12/7224/580/677777bcF6415526b/d9d3747bae39b392.png":5,
    "https://img10.360buyimg.com/img/jfs/t1/267458/18/7419/769/67777c27Ff5f45d09/eba279fffaf5a4dd.png":4,
    "https://img14.360buyimg.com/img/jfs/t1/256922/10/7462/773/67777c27F54a3d7e1/904af42830e12750.png":3,
    "https://img12.360buyimg.com/img/jfs/t1/268183/19/7308/779/67777c27Fa32125f7/7021b7b91e5b4ff3.png":2,
    "https://img11.360buyimg.com/img/jfs/t1/262906/21/7318/752/67777c27F29a5d6da/17fa37516a580e1e.png":1,
}
"""变量区"""""""""""""""""""""""""""""""""""""""""""""

"""函数区"""""""""""""""""""""""""""""""""""""""""""""
def init_csv():
    """初始化CSV文件，如果文件不存在则创建并写入表头"""
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow([
                '用户名', 'Plus标识', '多次购买标识', '评价星级',
                '初次评论时间', '产品型号', '使用后标识', '初次评论',
                '初评-追评时间间隔', '追加评论', '回复数', '点赞数','图片数量','当前模块'
            ])
        print(f"已创建CSV文件: {csv_file}")

def save_to_csv(data):
    """保存单条数据到CSV文件"""
    with open(csv_file, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(data)
    print(f"已保存数据: {data[0]} - {data[3]}星")

def calculate_time_interval(initial_time, follow_time):
    """计算初次评论和追评的时间间隔（天数）"""
    if not follow_time or follow_time == '':
        return ''
    
    try:
        # 假设时间格式为 "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM:SS"
        # 根据实际格式调整
        initial_date = datetime.strptime(initial_time, '%Y-%m-%d')
        follow_date = datetime.strptime(follow_time, '%Y-%m-%d')
        days_diff = (follow_date - initial_date).days
        return f"{days_diff}天"
    except:
        return follow_time  # 如果解析失败，返回原始时间

"""函数区"""""""""""""""""""""""""""""""""""""""""""""

"""主流程"""""""""""""""""""""""""""""""""""""""""""""
if __name__ == "__main__":
    # 初始化CSV文件
    init_csv()
    
    # tab.get('https://www.jd.com/')
    # tab.ele("@class=asdf",timeout=0.1).click()
    input("? 检查登录情况->")
    
    plIds=[]
    while 1:
        try:
            plBox=tab.ele("@class=_list_1ygkr_67",timeout=0.1)
            pt='京东'
            spUrl=tab.url
            spTitle=''
            dpName=''
            dpId=''
            spId=''

            if plBox:
                plEles=plBox.child().child().child().child().children()
                for plItem in plEles:
                    sy='否'
                    xx=0
                    cz='否'
                    name=''
                    dc='否'
                    plus='否'
                    ccsj=''
                    cpxh=''
                    hfNum=0
                    dzNum=0
                    cp=''
                    zpSj=''
                    zpContent=''
                    imgNum=''
                    type=''

                    # 当前模块
                    typeEle=tab.ele("@class=_tag_rgt47_12 _tag-active_rgt47_31",timeout=0.1)
                    if typeEle:
                        type=typeEle.text

                    # 使用后
                    syEle=plItem.ele("@class=jdc-pc-rate-card-watermark",timeout=0.01)
                    if syEle:
                        sy='是'
                    print("使用后:",sy)

                    # 星星
                    imgs=plItem.eles("@tag()=img",timeout=0.1)
                    for imgItem in imgs:
                        if imgItem.attr('alt')=='star':
                            xx=xj.get(imgItem.link,0)
                    print("星星",xx)

                    # 超赞
                    czEle=plItem.ele("@class=jdc-pc-icon-star-good mr star-good-1",timeout=0.01)
                    if czEle:
                        cz='是'
                    print("超赞",cz)

                    # 用户名
                    nameEle=plItem.ele("@class=jdc-pc-rate-card-nick",timeout=0.1)
                    if nameEle:
                        name=nameEle.text
                    print("用户名",name)

                    # 多次购买
                    dcEle=plItem.ele("@class=jd-content-pc-tag ",timeout=0.01)
                    if dcEle:
                        dc='是'
                    print("多次购买",dc)

                    # plus
                    plusEle=plItem.ele("@class=jdc-avatar plus",timeout=0.01)
                    if plusEle:
                        plus='是'
                    print("plus",plus)

                    # 初次评论时间
                    ccsjEle=plItem.ele("@class=date list",timeout=0.1)
                    if ccsjEle:
                        ccsj=ccsjEle.text
                    print("初次评论时间",ccsj)

                    # 产品型号
                    cpxhEle=plItem.ele("@class=info",timeout=0.1)
                    if cpxhEle:
                        cpxh=cpxhEle.text
                    print('产品型号',cpxh)

                    # 2指标
                    zb2=plItem.eles("@class=jdc-count",timeout=0.1)
                    if len(zb2)==2:
                        hfNum=zb2[0].text
                        if hfNum=='回复':
                            hfNum=0
                        dzNum=zb2[1].text
                        if dzNum=='有用':
                            dzNum=0
                    print(f"回复:{hfNum},点赞:{dzNum}")
                    

                    # 初次评论
                    cpEle=plItem.ele("@class=jdc-pc-rate-card-main",timeout=0.1)
                    if cpEle:
                        cp=cpEle.text
                    print('初评',cp)

                    # 追评
                    zpSj=''
                    zpContent=''
                    zpBoxEle=plItem.ele("@class=jdc-pc-rate-card-after",timeout=0.01)
                    if zpBoxEle:
                        zpData=zpBoxEle.children()
                        if len(zpData) >= 2:
                            zpSj=zpData[0].text
                            zpContent=zpData[1].text
                        elif len(zpData) == 1:
                            zpSj=zpData[0].text
                            zpContent=''
                    print(f"追评时间:{zpSj},{zpContent}")

                    # 计算时间间隔
                    time_interval = calculate_time_interval(ccsj, zpSj) if zpSj else ''

                    # 图片数量
                    imgEle=plItem.ele("@class=jd-content-pc-media-list",timeout=0.1)
                    if imgEle:
                        imgNum=len(imgEle.children())
                    
                    # 生成唯一ID用于去重
                    plId = name + cp + type
                    if plId in plIds:
                        print(f"重复数据，跳过: {name}")
                        continue
                    else:
                        plIds.append(plId)
                        # 准备要保存的数据
                        csv_data = [
                            name,           # 用户名
                            plus,           # Plus标识
                            dc,             # 多次购买标识
                            xx,             # 评价星级
                            ccsj,           # 初次评论时间
                            cpxh,           # 产品型号
                            sy,             # 使用后标识
                            cp,             # 初次评论
                            time_interval,  # 初评-追评时间间隔
                            zpContent,      # 追加评论
                            hfNum,          # 回复数
                            dzNum,           # 点赞数
                            imgNum,         # 图片数量
                            type            # 当前模块
                        ]
                        # 保存到CSV
                        save_to_csv(csv_data)
                        print("="*50)
                        
        except Exception as e:
            print(f"采集出错: {e}")
            pass