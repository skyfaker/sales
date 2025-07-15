import streamlit as st
import pandas as pd
import re

st.title("文件上传与处理工具")

# 限制上传类型
file_types = ["csv", "xlsx"]

# 上传数据文件
data_file = st.file_uploader("上传数据文件", type=file_types, key="data_file")

# 上传映射文件
mapping_file = st.file_uploader("上传映射文件", type=file_types, key="mapping_file")

# 读取pandas csv文件


def read_file(file, remove_col=False):
    if file.name.endswith(".csv"):
        df_all = pd.read_csv(file)
    elif file.name.endswith(".xlsx"):
        df_all = pd.read_excel(file)
    else:
        return None

    if remove_col:
        reserved_col = ["日期", "客户", "物料名称", "实发数量", "含税单价", "价税合计", "单据编号"]
        df_new = df_all[reserved_col]
        del df_all
        st.success("✅ 已删除无关列")
        return df_new
    else:
        return df_all


# 展示预览
if data_file:
    st.subheader("数据文件预览")
    data_df = read_file(data_file, remove_col=True)
    st.dataframe(data_df.head(10))
else:
    data_df = None

if mapping_file:
    st.subheader("映射文件预览")
    mapping_df = read_file(mapping_file)
    st.dataframe(mapping_df.head(10))
else:
    mapping_df = None

# 处理按钮
if data_file and mapping_file:
    if st.button("开始处理文档"):
        st.subheader("处理结果")

        st.write("✅ 已读取数据文件和映射文件")

        try:
            # 1. 向下填充空白字段
            df = data_df.ffill()

            # 2. 删除最后一行如果“日期”列为“合计”
            date_column = "日期"
            if date_column in df.columns:
                last_value = str(df[date_column].iloc[-1]).strip()
                if last_value == "合计":
                    df = df.iloc[:-1]
                    st.info("最后一行日期字段为“合计”，已删除该行。")

            # 3. 插入“型号简称”列在“物料名称”之后
            material_col = "物料名称"
            alias_col = "型号简称"

            if material_col not in df.columns:
                st.error(f"❌ 数据文件中未找到列 '{material_col}'，无法插入型号简称列。")
            elif material_col not in mapping_df.columns or alias_col not in mapping_df.columns:
                st.error(f"❌ 映射文件中必须包含列 '{material_col}' 和 '{alias_col}'。")
            else:
                # 创建映射字典
                mapping_dict = dict(zip(mapping_df[material_col], mapping_df[alias_col]))

                # 使用映射，未匹配的填“无”
                alias_series = df[material_col].map(mapping_dict).fillna("无")

                # 插入型号简称列到物料名称之后
                insert_loc = df.columns.get_loc(material_col) + 1
                df.insert(insert_loc, alias_col, alias_series)

                st.success("✅ 型号简称列插入成功")

            # 4. 插入 年、月、日 三列在 日期 之后
            if date_column in df.columns:
                # 确保为字符串并分割
                date_parts = df[date_column].astype(str).str.strip().str.split("/", expand=True)
                if date_parts.shape[1] == 3:
                    year_col, month_col, day_col = "年", "月", "日"
                    date_index = df.columns.get_loc(date_column) + 1
                    try:
                        df.insert(date_index, year_col, date_parts[0])
                        df.insert(date_index + 1, month_col, date_parts[1])
                        df.insert(date_index + 2, day_col, date_parts[2])
                        st.success("✅ 已提取日期为 年、月、日 列")
                    except Exception as e:
                        print(e)
                else:
                    st.warning("⚠️ 日期字段格式不正确，无法拆分为 年/月/日")
            else:
                st.warning("⚠️ 未找到日期字段，无法提取年月日")

            # 5. 按日期降序排序
            try:
                df[date_column] = pd.to_datetime(df[date_column], format="%Y/%m/%d", errors="coerce")
                df = df.sort_values(by=date_column, ascending=False)
                df[date_column] = df[date_column].dt.strftime("%Y/%m/%d")  # 恢复为字符串格式
                st.success("✅ 已按日期降序排序")
            except Exception as e:
                st.warning(f"⚠️ 日期排序失败：{e}")

            # 6. 正则表达式 - 处理物料名称列
            def clean_title(text):
                text = re.sub(r'^(品胜-|品胜严选-|PISEN[- (PRO|QUICK)]*|移动电源 PISEN QUICK\s*)', '', text, flags=re.IGNORECASE)
                text = re.sub(r'(纸盒装|(纸质|通用)?彩盒|牛皮盒装|天地盒装|气泡袋).*$', '', text)
                return text.strip()

            df['物料名称'] = df['物料名称'].apply(clean_title)

            # 显示结果
            st.dataframe(df)

            # 下载按钮
            st.download_button(
                label="下载处理后的文件（CSV）",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="processed_data.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"处理过程中出错：{e}")
else:
    st.warning("请先上传两个文件以启用处理按钮")
