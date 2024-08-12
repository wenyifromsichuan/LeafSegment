import cv2
import numpy as np
import os
import pandas as pd

def ensure_dir(directory):
    """确保目录存在，不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def process_red_mask(hsv_image, file_name, file_extension):
    """
    处理红色掩膜，计算圆形红色标志物的面积
    """
    # 定义红色范围
    red_lower1 = np.array([0, 100, 100])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 100, 100])
    red_upper2 = np.array([180, 255, 255])

    # 创建红色掩膜
    red_mask1 = cv2.inRange(hsv_image, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv_image, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)

    # 查找红色掩膜的轮廓
    red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    circular_red_area = 0
    if red_contours:
        # 找到最大轮廓
        largest_contour = max(red_contours, key=cv2.contourArea)

        # 创建一个全黑的掩膜图像，大小与原图像相同
        circular_red_mask = np.zeros_like(red_mask)

        # 计算轮廓的最小外接圆
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        center = (int(x), int(y))
        radius = int(radius)

        # 计算圆形掩膜
        cv2.circle(circular_red_mask, center, radius, (255), thickness=-1)

        # 保存圆形掩膜图像
        circular_red_mask_dir = "red_masks/circular"
        ensure_dir(circular_red_mask_dir)
        circular_red_mask_filename = os.path.join(circular_red_mask_dir, f'{file_name}_circular_red_mask{file_extension}')
        cv2.imwrite(circular_red_mask_filename, circular_red_mask)

        # 计算圆形红色标志物的面积
        circular_red_contours, _ = cv2.findContours(circular_red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        circular_red_area = sum(cv2.contourArea(contour) for contour in circular_red_contours)

    # 保存原始红色掩膜图像
    red_mask_dir = "red_masks/original"
    ensure_dir(red_mask_dir)
    red_mask_filename = os.path.join(red_mask_dir, f'{file_name}_red_mask{file_extension}')
    cv2.imwrite(red_mask_filename, red_mask)

    return circular_red_area

def process_non_black_mask(hsv_image, file_name, file_extension):
    """
    处理非黑色掩膜，计算封闭非黑色区域的面积，并去除所有黑色部分
    """
    # 定义黑色范围
    black_lower = np.array([0, 0, 0])
    black_upper = np.array([180, 255, 150])  # 定义亮度阈值低于150的区域为黑色

    # 创建黑色掩膜
    black_mask = cv2.inRange(hsv_image, black_lower, black_upper)

    # 反转黑色掩膜，得到非黑色掩膜
    non_black_mask = cv2.bitwise_not(black_mask)

    # 腐蚀和膨胀
    kernel = np.ones((1, 1), np.uint8)
    non_black_mask_eroded = cv2.erode(non_black_mask, kernel, iterations=3)
    non_black_mask_dilated = cv2.dilate(non_black_mask_eroded, kernel, iterations=3)

    # 查找非黑色掩膜的轮廓
    non_black_contours, _ = cv2.findContours(non_black_mask_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 创建一个全黑的掩膜图像，大小与非黑色掩膜相同
    closed_non_black_mask = np.zeros_like(non_black_mask_dilated)

    # 填充非黑色掩膜中的所有轮廓
    for contour in non_black_contours:
        cv2.drawContours(closed_non_black_mask, [contour], -1, (255), thickness=cv2.FILLED)

    # 去除 closed_non_black_mask 中的黑色部分
    closed_non_black_mask = cv2.bitwise_and(closed_non_black_mask, closed_non_black_mask, mask=non_black_mask_dilated)

    # 查找所有填充后的非黑色区域的轮廓
    closed_non_black_contours, _ = cv2.findContours(closed_non_black_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 过滤掉面积小于100的区域
    filtered_mask = np.zeros_like(closed_non_black_mask)
    for contour in closed_non_black_contours:
        if cv2.contourArea(contour) >= 1500:
            cv2.drawContours(filtered_mask, [contour], -1, (255), thickness=cv2.FILLED)

    # 计算过滤后的非黑色区域面积
    filtered_non_black_contours, _ = cv2.findContours(filtered_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    closed_non_black_area = sum(cv2.contourArea(contour) for contour in filtered_non_black_contours)

    # 保存填充并去除黑色后的非黑色掩膜图像
    closed_non_black_mask_dir = "non_black_masks/closed"
    ensure_dir(closed_non_black_mask_dir)
    closed_non_black_mask_filename = os.path.join(closed_non_black_mask_dir, f'{file_name}_closed_non_black_mask{file_extension}')
    cv2.imwrite(closed_non_black_mask_filename, filtered_mask)

    # 保存原始非黑色掩膜图像
    non_black_mask_dir = "non_black_masks/original"
    ensure_dir(non_black_mask_dir)
    non_black_mask_filename = os.path.join(non_black_mask_dir, f'{file_name}_non_black_mask{file_extension}')
    cv2.imwrite(non_black_mask_filename, non_black_mask)

    return closed_non_black_area

def process_images_in_directory(directory):
    """
    处理目录中的所有图像文件，并将结果保存到 Excel 文件中
    """
    results = []

    # 遍历目录中的所有文件
    for file_name in os.listdir(directory):
        if file_name.lower().endswith('.jpg'):
            image_path = os.path.join(directory, file_name)

            # 加载图像
            image = cv2.imread(image_path)
            if image is None:
                print(f"无法加载图像: {image_path}")
                continue

            # 提取文件名（不包含扩展名）
            base_file_name, file_extension = os.path.splitext(file_name)

            # 转换为HSV颜色空间
            hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # 处理红色掩膜
            circular_red_area = process_red_mask(hsv_image, base_file_name, file_extension)

            # 处理非黑色掩膜
            closed_non_black_area = process_non_black_mask(hsv_image, base_file_name, file_extension)

            # 计算实际非黑色区域面积
            known_red_area = 11309.73
            if circular_red_area > 0:
                non_black_area = known_red_area * (closed_non_black_area - circular_red_area) / circular_red_area
            else:
                non_black_area = 0
                print(f"红色标志物面积为零，无法计算实际非黑色区域面积。")

            # 收集结果
            results.append({
                '文件名': base_file_name,
                '红色标志物面积（像素）': circular_red_area,
                '封闭非黑色区域面积（像素）': closed_non_black_area,
                '实际非黑色区域面积（平方毫米）': non_black_area
            })

    # 保存到 Excel 文件
    df = pd.DataFrame(results)
    excel_filename = 'results.xlsx'
    if not os.path.exists(excel_filename):
        df.to_excel(excel_filename, index=False)
    else:
        # 如果文件已存在，追加数据
        with pd.ExcelWriter(excel_filename, mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False, header=False, startrow=writer.sheets['Sheet1'].max_row)

if __name__ == "__main__":
    # 请将'directory_path'替换为实际的目录路径
    directory_path = r'D:\20240426\20240403-0501\images'
    process_images_in_directory(directory_path)
