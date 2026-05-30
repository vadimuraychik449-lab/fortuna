# Временно добавьте в начало функции start:
if update.effective_chat.id < 0:
    print(f"ID группы: {update.effective_chat.id}")
