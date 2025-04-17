import fastf1

# セッションを取得（2025年 鈴鹿の予選）
session = fastf1.get_session(2025, 'Suzuka', 'Q')
session.load()  

print(session.name)  
print(session.date)  
