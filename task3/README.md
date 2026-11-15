# Task 3 — Kakuro CSP

Tài liệu học từ lý thuyết đến từng hàm và luyện vấn đáp:
[HOC_VA_VAN_DAP.md](HOC_VA_VAN_DAP.md).

Chỉ triển khai Task 3. Nguồn đề: `2627-HK1-AI-CK.pdf`, trang 4–6;
testcase phức tạp là hình 9×9 ở trang 5, được đọc trực tiếp từ ảnh trang PDF.
Trang 7 của đề ghi cấm sử dụng công cụ AI; người sử dụng cần tuân thủ quy định
môn học trước khi dùng sản phẩm này cho bài nộp.

## 1. Phân tích mô hình CSP

Quy ước tọa độ trong tài liệu: hàng/cột **bắt đầu từ 1**. Trong JSON/Python,
chỉ số bắt đầu từ 0. Kích thước 9×9 bao gồm cả ô xám/ô gợi ý.

- **X**: 48 biến `X[r,c]`, mỗi biến tương ứng đúng một ô trắng.
- **D**: ban đầu mỗi biến có miền `{1,2,3,4,5,6,7,8,9}`.
- **C**: 28 nhóm liên tiếp, gồm 14 nhóm ngang và 14 nhóm dọc.
  Mỗi nhóm có hai điều kiện: tổng bằng gợi ý và tất cả chữ số khác nhau.
  Do đó có 56 điều kiện logic, biểu diễn bằng 28 `SumConstraint` kết hợp.
- Mỗi ô trắng thuộc đúng một nhóm ngang và một nhóm dọc. Các chữ số được
  phép lặp ở các nhóm khác nhau; không áp dụng All-Different cho toàn hàng/cột
  nếu giữa chúng có ô xám ngăn cách.
- Đường chéo đi từ góc trên trái xuống góc dưới phải. Số **trên phải** chỉ tổng
  ngang, số **dưới trái** chỉ tổng dọc. Ô `#` không sinh biến hay ràng buộc.

Với mỗi nhóm S có tổng gợi ý t:

```text
sum(X for X in S) = t
AllDifferent(S)
```

Các nhóm ngang đã đối chiếu với hình PDF:

| Ô gợi ý | Các ô trắng | Tổng |
|---|---|---:|
| (2,2) | (2,3)…(2,5) | 22 |
| (2,6) | (2,7)…(2,8) | 3 |
| (3,2) | (3,3)…(3,9) | 28 |
| (4,1) | (4,2)…(4,3) | 14 |
| (4,5) | (4,6)…(4,9) | 20 |
| (5,1) | (5,2)…(5,3) | 17 |
| (5,4) | (5,5)…(5,8) | 22 |
| (6,2) | (6,3)…(6,6) | 28 |
| (6,7) | (6,8)…(6,9) | 12 |
| (7,1) | (7,2)…(7,5) | 14 |
| (7,7) | (7,8)…(7,9) | 6 |
| (8,1) | (8,2)…(8,8) | 39 |
| (9,2) | (9,3)…(9,4) | 16 |
| (9,5) | (9,6)…(9,8) | 8 |

Các nhóm dọc:

| Ô gợi ý | Các ô trắng | Tổng |
|---|---|---:|
| (1,3) | (2,3)…(9,3) | 44 |
| (1,4) | (2,4)…(3,4) | 16 |
| (1,5) | (2,5)…(3,5) | 9 |
| (1,7) | (2,7)…(5,7) | 15 |
| (1,8) | (2,8)…(9,8) | 44 |
| (2,6) | (3,6)…(6,6) | 11 |
| (2,9) | (3,9)…(4,9) | 14 |
| (3,2) | (4,2)…(5,2) | 17 |
| (4,5) | (5,5)…(8,5) | 12 |
| (5,4) | (6,4)…(9,4) | 29 |
| (5,9) | (6,9)…(7,9) | 7 |
| (6,2) | (7,2)…(8,2) | 12 |
| (7,6) | (8,6)…(9,6) | 7 |
| (7,7) | (8,7)…(9,7) | 12 |

## 2. Thuật toán

1. **GAC ban đầu**: đưa tất cả nhóm vào hàng đợi. Trong mỗi nhóm, giữ một
   giá trị của biến khi tồn tại một phép gán đầy đủ trong miền hiện tại thỏa
   cả tổng và All-Different. Khi miền bị thu hẹp, đưa nhóm giao nhau vào lại
   hàng đợi. Dừng khi đạt điểm cố định hoặc xuất hiện miền rỗng.
2. **MRV**: chọn biến chưa gán có miền nhỏ nhất. **Degree** phá hòa bằng số
   biến láng giềng chưa gán lớn nhất, tính mỗi láng giềng một lần.
   Hòa tiếp thì chọn theo hàng/cột để có kết quả lặp lại được.
3. **LCV**: thử tính hỗ trợ cho từng giá trị trên các nhóm chứa biến; ưu tiên
   giá trị loại ít giá trị của láng giềng chưa gán nhất. Đây là ước lượng cục
   bộ, không chạy tìm kiếm con và không thay đổi trạng thái thật.
4. Gán giá trị và thu miền biến về singleton; chạy lại **GAC** từ các nhóm
   chứa biến vừa gán, rồi đệ quy **Backtracking Search**.
5. Nếu thất bại, phát sự kiện đỏ, khôi phục giá trị và toàn bộ miền về snapshot
   trước nhánh rồi thử giá trị tiếp theo. Nếu mọi nhánh thất bại, trả vô nghiệm.
6. Chỉ chấp nhận nghiệm khi tất cả biến đã gán và tất cả nhóm đều thỏa mãn.

GAC áp dụng cho ràng buộc n-ngôi; không gọi AC-3 nhị phân trực tiếp lên tổng.
Việc tìm hỗ trợ dùng DFS có ghi nhớ trạng thái `(index, used_digits, sum_left)`
và chặn bằng cận tổng các chữ số chưa dùng. Đây là cách triển khai phép kiểm tra
hỗ trợ của GAC, không phải thuật toán tìm kiếm thay thế. Cache chỉ sống trong
một lần lọc nhóm, không lưu tất cả hoán vị hay toàn bộ lịch sử sự kiện.

GAC chỉ xóa giá trị không có hỗ trợ nên bảo toàn nghiệm. Quay lui xét đủ miền
còn lại và khôi phục chính xác trạng thái trước nhánh, nên tìm kiếm đầy đủ trên
bài toán hữu hạn. Độ phức tạp xấu nhất vẫn là hàm mũ; không cam kết tốc độ cho
mọi bàn Kakuro. Chiều sâu đệ quy trên testcase là tối đa 48 lần gán.

## 3. Kiến trúc MVC và Observer

```text
models/variable.py       Variable: vị trí, value, domain, prune/restore
models/constraint.py     SumConstraint: Sum + All-Different, GAC supports
models/board.py          KakuroBoard: JSON, validation, constraint graph
solver/heuristics.py     MRV / Degree / LCV
solver/propagation.py    Hàng đợi GAC và phát sự kiện prune/conflict
solver/backtracking.py   CSPSolver: controller tìm kiếm và snapshot phục hồi
solver/callback.py       SolverCallback Protocol, SolverEvent bất biến
ui/visualizer.py         KakuroVisualizer: View + controller bàn phím/chuột
test_cases/              Bàn PDF và bàn vô nghiệm tổng hợp để minh họa quay lui
tests/                  Kiểm tra solver và giao diện
docs/                   Ảnh giao diện, số đo thực tế
main.py                 Ghép model/controller/view, CLI
```

Solver không import Pygame và có thể chạy độc lập. View triển khai
`SolverCallback.on_event()` để nhận thay đổi. `events()` là generator lười:
mỗi `next()` thực hiện tới đúng một sự kiện, không tính trước lời giải và không
tích trữ hàng nghìn frame. UI đọc model hiện tại sau mỗi sự kiện. Các phép thăm
dò LCV không phát sự kiện. Khi Reset/đóng cửa sổ, generator được đóng; trạng thái
đang giải dở được phục hồi. Callback lỗi cũng có cleanup.

Giao diện giữ vòng lặp 60 FPS và không dùng `sleep()` để tạo delay. Mỗi frame
chạy tối đa một sự kiện đến hạn. Các phép tính giữa hai sự kiện vẫn chạy đồng
bộ; không có cam kết UI thời gian thực cho bàn tùy ý quá lớn.

Mỗi lớp/hàm được viết có docstring nêu mục đích, tham số và kết quả; không dùng
NumPy vì các phép toán ở đây chỉ cần cấu trúc dữ liệu chuẩn Python.

## 4. Cài đặt và chạy

Yêu cầu **Python 3.10 trở lên**. Mở terminal tại thư mục **task3**, nơi chứa
thư mục `source`, rồi thực hiện theo thứ tự dưới đây.

### Windows PowerShell

**Bước 1 — Tạo môi trường ảo:**

```powershell
python -m venv .venv
```

Nếu máy không nhận lệnh `python`, dùng `py -m venv .venv` ở bước này.

**Bước 2 — Kích hoạt môi trường ảo:**

```powershell
.\.venv\Scripts\Activate.ps1
```

Khi kích hoạt thành công, terminal thường hiển thị `(.venv)` ở đầu dòng.
Nếu dùng **Command Prompt (CMD)**, thay lệnh kích hoạt bằng:

```cmd
.venv\Scripts\activate.bat
```

**Bước 3 — Cài Pygame trong môi trường ảo:**

```powershell
python -m pip install -r source/task_3/requirements.txt
```

Lệnh trên cài `pygame==2.6.1` theo cấu hình dự án.

**Bước 4 — Chạy chương trình:**

```powershell
python source/task_3/main.py
```

### macOS hoặc Linux

**Tạo và kích hoạt môi trường ảo:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Cài Pygame và chạy chương trình:**

```bash
python -m pip install -r source/task_3/requirements.txt
python source/task_3/main.py
```

### Những lần chạy tiếp theo

Không cần tạo lại môi trường hoặc cài lại Pygame. Khi mở terminal mới,
đứng tại thư mục `task3`, kích hoạt lại môi trường rồi chạy:

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
python source/task_3/main.py
```

**macOS hoặc Linux:**

```bash
source .venv/bin/activate
python source/task_3/main.py
```

### Chạy không có giao diện

Sau khi đã kích hoạt môi trường ảo:

```bash
python source/task_3/main.py --headless
```

Để thoát môi trường ảo sau khi sử dụng:

```bash
deactivate
```

Đường dẫn testcase mặc định được lấy theo vị trí `main.py`, không phụ thuộc
thư mục khởi chạy. Các lệnh bên trên dùng đường dẫn tương đối từ thư mục `task3`.

Điều khiển:

| Nút/phím | Tác dụng |
|---|---|
| Play / Pause, Space | Chạy hoặc tạm dừng; ban đầu tạm dừng để quan sát miền |
| Step, N | Tạm dừng và tiến đúng một sự kiện |
| Reset, R | Hủy lần giải hiện tại, khôi phục miền `{1,…,9}` |
| Thanh Delay | Kéo chuột để chọn 0–500 ms; 0 ms vẫn giới hạn một sự kiện/frame |
| Esc, đóng cửa sổ | Thoát và giải phóng Pygame |

Miền hiện dưới dạng 9 pencil marks; cam = GAC loại giá trị, xanh lá = gán thử,
đỏ = xung đột/quay lui, xanh nhạt = phục hồi miền. Sự kiện đỏ được hiển thị
trước sự kiện khôi phục, kể cả khi chạy tự động. Thời gian `Compute` loại trừ
thời gian Pause/Delay và vẽ UI.

**Lưu ý minh họa:** GAC giải hết miền của testcase PDF về singleton, vì vậy
testcase này không phát sinh nhánh sai và bộ đếm Backtracks bằng 0. Để quan sát
quay lui thật trên một bàn vô nghiệm tổng hợp (không thuộc PDF):

```powershell
python source/task_3/main.py --board source/task_3/test_cases/board_unsatisfiable.json --delay 10
```

## 5. Kiểm chứng và kết quả đo

```powershell
$env:PYTHONPATH = 'source/task_3'
python -m unittest discover -s source/task_3/tests -v
```

Trên macOS/Linux: `PYTHONPATH=source/task_3 python -m unittest discover -s source/task_3/tests -v`.

8 kiểm thử đạt:

- Duyệt trực tiếp các gợi ý JSON, kiểm tra từng chữ số 1–9, tổng và không trùng
  của đủ 28 nhóm, độc lập với hàm `is_solved()`.
- So hỗ trợ GAC với vét cạn tích Descartes của 60 cấu hình miền ngẫu nhiên có
  seed cố định, độ dài nhóm 2–4.
- Kiểm tra MRV, Degree, thứ tự LCV và việc thăm dò không sửa miền thật.
- Bàn vô nghiệm tổng hợp: 325 lần gán/quay lui; kiểm tra domain rỗng khi có
  conflict và toàn bộ miền/giá trị phục hồi sau khi kết thúc.
- Hủy generator và callback ném ngoại lệ đều phục hồi trạng thái.
- Giải lặp 25 lần cho cùng nghiệm và từ chối cấu hình sai.
- Pygame dùng SDL dummy: render, Step, Play/Pause, kéo slider, Reset, giải hết,
  vẽ sự kiện đỏ và thoát. Đây là kiểm thử không cần màn hình; chưa phải phiên
  thao tác thủ công trên cửa sổ desktop hay kiểm tra trên macOS chấm bài.

Đo bổ sung trên runtime Windows hiện tại, kết quả lưu `docs/validation.json`:

| Đại lượng | Kết quả |
|---|---:|
| Số lần giải đúng testcase PDF | 100/100 |
| Thời gian trung vị không UI | 17,49 ms |
| Nhỏ nhất / lớn nhất | 16,81 / 21,56 ms |
| Số lần gán / quay lui mỗi lần giải | 48 / 0 |
| Số giá trị bị GAC xóa mỗi lần giải | 384 |
| Bộ nhớ Python đỉnh qua 50 lần giải có tracemalloc | 1.111.078 byte |
| Bộ nhớ còn được theo dõi sau GC | 10.368 byte |

Phép đo bộ nhớ chỉ bao gồm cấp phát Python trong khoảng theo dõi, không phải
RSS toàn tiến trình hoặc bộ nhớ SDL. Không suy rộng số đo Windows thành kết quả
trên Intel Core i5/macOS 13.7.8 được nêu trong đề.

Nghiệm thu được (`#` thay cho mọi ô không phải ô trắng):

```text
# # # # # # # # #
# # 5 9 8 # 1 2 #
# # 2 7 1 3 4 6 5
# 8 6 # # 1 2 8 9
# 9 8 # 3 2 8 9 #
# # 9 8 6 5 # 7 5
# 3 4 5 2 # # 4 2
# 9 3 7 1 6 8 5 #
# # 7 9 # 1 4 3 #
```

Ảnh đã kiểm tra bằng mắt: `docs/domains.png`, `docs/propagation.png`,
`docs/solution.png`.
