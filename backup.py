import streamlit as st
from streamlit_drawable_canvas import st_canvas
import numpy as np
import json

st.set_page_config(
    page_title="PAInt App",
    page_icon="🔞",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("PAInt App")

# サイドバーでパラメータを指定
stroke_width = st.sidebar.slider("Stroke width: ", 1, 25, 3)
stroke_color = st.sidebar.color_picker("Stroke color hex: ", "#000000")
bg_color = st.sidebar.color_picker("Background color hex: ", "#FFFFFF")

# JSONデータの読み込み（キャッシュを利用）
@st.cache_data
def load_shape_data():
    with open("shape_data.json") as f:
        return json.load(f)

shape_data = load_shape_data()  # キャッシュされたJSONデータを取得

# セッションステートの初期化
if "objects" not in st.session_state:
    st.session_state["objects"] = []  # 描画オブジェクトを保持する
if "rerun" not in st.session_state:
    st.session_state["rerun"] = False  # リラン管理用

# クリアボタンを追加
if st.sidebar.button("Clear Canvas"):
    st.session_state["objects"] = []  # 描画オブジェクトをクリア
    st.session_state["rerun"] = True  # リランをトリガー
    st.rerun()

# 2つの点の間の角度を計算
def calculate_angle(start_point, end_point):
    delta = end_point - start_point
    angle = np.arctan2(delta[1], delta[0])  # y, x を基に角度を計算
    return angle

# 回転行列を適用して座標を回転
def rotate_point(point, angle, origin):
    # 点を原点に移動して回転、その後再移動
    rotation_matrix = np.array([
        [np.cos(angle), -np.sin(angle)],
        [np.sin(angle), np.cos(angle)]
    ])
    translated_point = point - origin
    rotated_point = np.dot(rotation_matrix, translated_point)
    return rotated_point + origin

# JSONから読み込んだ形状データをスケーリングして回転する
def scale_and_rotate_shape_to_fit(json_data, drawn_start, drawn_end):
    if len(json_data) == 0:
        return []

    # JSONデータの始点と終点を取得
    start_point = np.array(json_data[0][1:3])  # JSONの最初のMの座標
    end_point = np.array(json_data[-1][-2:])   # JSONの最後のL/Qの座標

    # スケールの計算
    json_length = np.linalg.norm(end_point - start_point)
    drawn_length = np.linalg.norm(drawn_end - drawn_start)
    if json_length == 0:
        return []

    scale_factor = drawn_length / json_length

    # 回転角度を計算
    angle = calculate_angle(drawn_start, drawn_end)

    # JSONの座標をスケーリングし、回転して新しい座標に変換
    scaled_shape = []
    for command in json_data:
        if command[0] == "M" and len(command) >= 3:
            point = np.array([command[1], command[2]])
            scaled_point = (point - start_point) * scale_factor + drawn_start
            rotated_point = rotate_point(scaled_point, angle, drawn_start)
            scaled_shape.append({
                "type": "line",  # 移動だけだが、ラインオブジェクトとして保持
                "x1": rotated_point[0],
                "y1": rotated_point[1],
                "x2": rotated_point[0],
                "y2": rotated_point[1],
                "stroke": stroke_color,
                "strokeWidth": stroke_width,
            })
        elif (command[0] == "L" or command[0] == "Q") and len(command) >= 5:
            point1 = np.array([command[1], command[2]])
            point2 = np.array([command[3], command[4]])
            scaled_point1 = (point1 - start_point) * scale_factor + drawn_start
            scaled_point2 = (point2 - start_point) * scale_factor + drawn_start
            rotated_point1 = rotate_point(scaled_point1, angle, drawn_start)
            rotated_point2 = rotate_point(scaled_point2, angle, drawn_start)
            scaled_shape.append({
                "type": "line",
                "x1": rotated_point1[0],
                "y1": rotated_point1[1],
                "x2": rotated_point2[0],
                "y2": rotated_point2[1],
                "stroke": stroke_color,
                "strokeWidth": stroke_width,
            })
    return scaled_shape

# キャンバスの作成
canvas_result = st_canvas(
    stroke_width=stroke_width,
    stroke_color=stroke_color,
    background_color=bg_color,
    update_streamlit=True,
    height=800,
    width=1200,
    drawing_mode="freedraw",
    key="canvas", 
    initial_drawing={"objects": st.session_state["objects"]} if st.session_state["objects"] else None  # セッションステートのオブジェクトを反映
)

# 描画の更新処理
if canvas_result.json_data is not None and not st.session_state["rerun"]:
    objects = canvas_result.json_data['objects']
    new_objects = []
    
    for obj in objects:
        if obj['type'] == 'path':  # フリーハンドのパスを取得
            path_data = obj['path']

            # パスデータが空でないか確認
            if len(path_data) == 0:
                continue

            # x, y 座標を抽出
            path = np.array([[p[1], p[2]] for p in path_data if len(p) == 3])

            # 最初と最後の点を取得（パスが空でないことを確認）
            if len(path) > 1:
                start_point = path[0]
                end_point = path[-1]

                # JSONから読み込んだ形状をスケーリングして新しい座標に変換
                scaled_shape = scale_and_rotate_shape_to_fit(shape_data, start_point, end_point)

                # スケーリングされた図形をオブジェクトに追加
                new_objects.extend(scaled_shape)

    # セッションステートに保存して再描画をトリガー
    if new_objects:
        st.session_state["objects"].extend(new_objects)  # スケーリング結果をセッションステートに保存
        st.session_state["rerun"] = True  # リランをトリガー
        st.rerun()  # ページを再レンダリング

# リランが完了したらリセット
if st.session_state["rerun"]:
    st.session_state["rerun"] = False

# デバッグ: セッションステートに保存されたオブジェクトを表示
st.write("Session State Objects:", st.session_state["objects"])
