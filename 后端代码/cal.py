# 初始化变量
sum_of_numbers = 0.0
count = 0

# 打开文件
with open('average', 'r') as file:
    # 逐行读取文件
    for line in file:
        # 尝试将行转换为浮点数并累加
        try:
            number = float(line.strip())  # 去除可能的空白字符并转换为浮点数
            sum_of_numbers += number
            count += 1
        except ValueError:
            # 如果转换失败（不是数字），可以打印错误信息或忽略该行
            print(f"Warning: '{line.strip()}' is not a number and will be ignored.")

# 计算平均数
if count > 0:
    average = sum_of_numbers / count
    print(sum_of_numbers)
    print(count)
    print(f"The average of the numbers is: {average}")
else:
    print("The file is empty or contains no valid numbers.")