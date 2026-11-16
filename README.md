# Final IAI — Introduction to Artificial Intelligence

Repository này tập hợp ba bài toán độc lập của Final Project: N-Queens, Tank Battle và Kakuro. Mỗi task có mã nguồn, cách chạy và tài liệu riêng. README này giúp chọn đúng chương trình để demo, biết mỗi thuật toán giải quyết vấn đề gì và tìm được dữ liệu kiểm chứng. Chi tiết triển khai nằm trong README của từng task.

## Tổng quan ba task

| Task | Bài toán và mục tiêu | Kỹ thuật AI chính | Cách demo | Tài liệu chi tiết |
| --- | --- | --- | --- | --- |
| **1 — N-Queens** | Đặt N quân hậu trên bàn N × N sao cho không quân nào tấn công nhau | Mệnh đề logic, CNF, Glucose3 SAT, Standard và Improved Min-Conflicts | CLI, bàn cờ ASCII, benchmark và biểu đồ | [Task 1 README](task1/README.md) |
| **2 — Tank Battle** | Hai tác nhân ra quyết định trong game xe tăng theo lượt trên bản đồ 13 × 13 | Minimax, Alpha-Beta, hàm đánh giá heuristic | Pygame UI, trận đấu headless, benchmark | [Task 2 README](task2/README.md) |
| **3 — Kakuro** | Điền số vào các ô trắng để thỏa tổng gợi ý và không lặp trong mỗi nhóm | CSP, GAC, MRV, Degree, LCV, Backtracking | Pygame UI theo từng sự kiện hoặc solver headless | [Task 3 README](task3/README.md) |

Ba task chạy độc lập; không cần hoàn thành task trước để chạy task sau. Task 1 và Task 2 nhận lệnh từ **thư mục gốc repository**. Các lệnh trong README của Task 3 bắt đầu từ **thư mục task3**.

## Cấu trúc repository

    Final_IAI/
    ├── README.md                         # Tài liệu tổng quan này
    ├── task1/
    │   ├── main.py                       # CLI N-Queens
    │   ├── models/                       # CNF, bàn cờ và validator
    │   ├── solvers/                      # Glucose3 và Min-Conflicts
    │   ├── benchmarks/                   # Đo lặp, CSV/JSON, biểu đồ
    │   ├── tests/
    │   ├── results/                      # Dữ liệu và PNG của lần chạy đã lưu
    │   ├── requirements.txt
    │   └── README.md
    ├── task2/
    │   ├── main.py                       # GUI, headless match, benchmark
    │   ├── core/                         # Luật chơi và trạng thái
    │   ├── agents/                       # Các tác nhân tìm kiếm và plugin
    │   ├── maps/                         # Ba kịch bản bản đồ
    │   ├── ui/                           # Menu và hiển thị Pygame
    │   ├── experiments/                  # Benchmark, CSV và PNG
    │   ├── tests/
    │   ├── specs/                        # Đặc tả thay đổi giao diện
    │   ├── requirements.txt
    │   └── README.md
    └── task3/
        ├── README.md
        └── source/task_3/
            ├── main.py                   # GUI hoặc solver headless
            ├── models/                   # Biến, nhóm ràng buộc, bàn Kakuro
            ├── solver/                   # GAC, heuristic, backtracking
            ├── ui/                       # Trực quan hóa quá trình giải
            ├── test_cases/               # Bàn 9 × 9 và bàn vô nghiệm
            ├── tests/
            ├── docs/                     # Ảnh, số đo, báo cáo kiểm chứng
            └── requirements.txt

File .gitignore ở gốc áp dụng cho cả repository. Mỗi task giữ dependencies và hướng dẫn riêng để dễ chạy và đánh giá độc lập.

## Bắt đầu

### 1. Lấy mã nguồn và chọn Python

    git clone https://github.com/tactra2019-dot/Final_IAI.git
    cd Final_IAI
    python --version

Các README của task yêu cầu Python 3.10 trở lên. Nên dùng môi trường ảo riêng cho từng task vì Task 1 dùng PySAT, Task 2 dùng Pygame cùng thư viện phân tích dữ liệu, còn Task 3 ghim phiên bản Pygame của nó. Nếu một phiên bản Python không cài được dependency tương ứng, hãy dùng phiên bản Python có gói phù hợp trên hệ điều hành đang chạy.

Ví dụ tạo môi trường cho Task 1 trên Windows PowerShell:

    python -m venv task1\.venv
    .\task1\.venv\Scripts\python.exe -m pip install -r task1\requirements.txt
    .\task1\.venv\Scripts\python.exe -m task1.main sat 8

Trên macOS/Linux, thay đường dẫn Python của môi trường ảo bằng task1/.venv/bin/python. Làm tương tự với task2/.venv và task3/.venv khi chạy hai task còn lại. Các lệnh tiếp theo dùng từ python để chỉ interpreter của môi trường đã cài dependencies cho task đó.

### 2. Chạy Task 1 — N-Queens

Từ thư mục gốc repository:

    python -m pip install -r task1/requirements.txt
    python -m task1.main
    python -m task1.main stats 4
    python -m task1.main sat 8
    python -m task1.main standard 20 --seed 42
    python -m task1.main improved 20 --seed 42

Không chạy python -m task1.main khi terminal đang ở bên trong thư mục task1; Python sẽ không tìm thấy package cha. Lệnh export sau chạy cả SAT benchmark và so sánh Min-Conflicts, rồi ghi CSV, JSON và sáu PNG:

    python -m task1.main export --sizes 4,5,6,8,10,12,16,20,30,50 --repeats 3 --trials 10 --seed 42

**Mô hình:** mỗi ô là một biến Boolean. Bộ sinh CNF dùng pairwise clauses cho điều kiện nhiều nhất một quân hậu trên cùng hàng, cột hoặc đường chéo; mỗi hàng còn phải có ít nhất một hậu. Glucose3 giải công thức SAT và một validator độc lập kiểm tra bàn cờ. Standard Min-Conflicts chọn ngẫu nhiên một hậu đang xung đột; Improved ưu tiên hậu có nhiều xung đột nhất. Cả hai hỗ trợ random restarts và giới hạn bước.

**Xem thêm:** [mã CNF](task1/models/cnf.py), [hai solver](task1/solvers/), [lệnh và kiến trúc đầy đủ](task1/README.md).

### 3. Chạy Task 2 — Tank Battle

Từ thư mục gốc repository:

    python -m pip install -r task2/requirements.txt
    python -m task2.main                    # Mở giao diện Pygame
    python -m task2.main --headless         # Trận đấu trong terminal

Có thể chọn tác nhân, bản đồ và độ sâu tìm kiếm:

    python -m task2.main --headless --p1 HeuristicAlphaBetaAgent --p2 AlphaBetaAgent --map map2_tactical.txt --depth 3

Benchmark bốn cấu hình tìm kiếm trên ba bản đồ:

    python -m task2.main --benchmark

**Mô hình:** core giữ luật, thực thể và trạng thái game; agents quyết định hành động bằng Minimax hoặc Alpha-Beta, với hoặc không có heuristic; ui hiển thị menu và trận đấu; experiments đo thời gian, số nút duyệt, nhánh cắt tỉa và kết quả. Có thể đặt tác nhân tự viết vào [thư mục plugin](task2/agents/external/); xem hợp đồng plugin trong [Task 2 README](task2/README.md). Task 2 dùng pygame trên các phiên bản Python thấp hơn 3.14 và pygame-ce cho Python 3.14 theo file requirements hiện tại.

### 4. Chạy Task 3 — Kakuro

Đứng trong thư mục task3 như hướng dẫn của [Task 3 README](task3/README.md):

    cd task3
    python -m pip install -r source/task_3/requirements.txt
    python source/task_3/main.py             # Mở giao diện Pygame
    python source/task_3/main.py --headless  # In nghiệm trong terminal

Bàn mặc định là testcase 9 × 9 lưu ở [board_9x9.json](task3/source/task_3/test_cases/board_9x9.json). Có thể chỉ định bàn khác bằng tham số --board. [Bàn vô nghiệm](task3/source/task_3/test_cases/board_unsatisfiable.json) dùng để quan sát quá trình quay lui.

**Mô hình:** mỗi ô trắng là một biến có miền 1–9. Mỗi nhóm ngang/dọc phải có tổng bằng gợi ý và các số khác nhau. Solver áp dụng Generalized Arc Consistency (GAC) để lọc miền, MRV và Degree để chọn biến, LCV để xếp thứ tự giá trị, sau đó Backtracking Search. Giao diện hiển thị gán thử, loại giá trị, xung đột và phục hồi miền theo từng sự kiện.

## Kiểm thử và cách đọc kết quả

| Task | Lệnh kiểm tra | Điều được kiểm tra |
| --- | --- | --- |
| 1 | python -m pytest task1/tests -q | Công thức CNF, SAT/UNSAT, nghiệm hợp lệ, Min-Conflicts, export, CLI |
| 2 | python -m pytest task2/tests -q | Luật game, agents, maps, plugin, benchmark và UI offscreen |
| 3 | Từ task3/source/task_3: python -m unittest discover -s tests -v | Ràng buộc Kakuro, GAC, heuristic, solver, phục hồi trạng thái và UI |

Chạy test bằng đúng môi trường ảo đã cài dependencies của task tương ứng. Test UI của Task 2 và Task 3 cần import pygame và dùng SDL dummy; không cần mở cửa sổ khi chạy tự động.

| Task | Dữ liệu và hình ảnh đã lưu | Ý nghĩa |
| --- | --- | --- |
| 1 | [SAT JSON](task1/results/sat.json), [Min-Conflicts JSON](task1/results/min_conflicts.json), [CSV/PNG](task1/results/) | Thời gian tạo CNF tách khỏi thời gian Glucose3; từng trial, mean/median/stdev, success rate, bước và biểu đồ |
| 2 | [Benchmark CSV](task2/experiments/results/benchmark_results.csv), [biểu đồ](task2/experiments/results/) | So sánh thuật toán trên các kịch bản qua thời gian, số nút, cắt tỉa và kết quả trận đấu |
| 3 | [Validation JSON](task3/source/task_3/docs/validation.json), [số đo](task3/source/task_3/docs/report_measurements.json), [ảnh](task3/source/task_3/docs/) | Kiểm chứng nghiệm, thời gian giải, số lần gán/quay lui, lọc miền và trực quan hóa |

**Phạm vi của dữ liệu hiện lưu:** file kết quả Task 1 trong repository đang chứa một lần benchmark cho N=5; lệnh export ở trên tạo lại dữ liệu cho danh sách N rộng hơn. File validation của Task 3 ghi 100/100 lần giải đúng testcase trong lần đo đã lưu. Các con số thời gian phụ thuộc máy và cấu hình chạy; hãy đọc trường môi trường, seed và số lần lặp trong dữ liệu trước khi so sánh. Không suy ra heuristic luôn tốt hơn từ một lần chạy hoặc từ một kích thước bàn.

## Giới hạn và điểm cần trình bày

- **Task 1:** pairwise CNF tăng bậc ba theo N; Glucose3 có thể dao động thời gian tìm kiếm. Min-Conflicts với giới hạn bước và restart không bảo đảm luôn tìm được nghiệm dù nghiệm tồn tại.
- **Task 2:** độ sâu tìm kiếm ảnh hưởng mạnh đến thời gian và số nút. Kết quả benchmark gắn với bản đồ, cặp tác nhân và cấu hình cụ thể. GUI cần Pygame; chế độ headless có thể chạy riêng.
- **Task 3:** Backtracking có độ phức tạp xấu nhất theo hàm mũ. Bàn mặc định được GAC giải gần hết trước khi phân nhánh, vì vậy dùng bàn vô nghiệm riêng nếu muốn quan sát quay lui. GUI cần Pygame; bộ giải headless tách khỏi giao diện.
- Các biểu đồ và số đo đã lưu là kết quả của môi trường ghi trong file dữ liệu, không phải cam kết hiệu năng trên mọi máy. Hướng dẫn chi tiết về thuật toán, điều khiển UI, benchmark và giới hạn nằm trong README của từng task.

Khi demo hoặc vấn đáp, hãy giải thích **biểu diễn trạng thái**, **ràng buộc/luật chuyển trạng thái**, **cách thuật toán chọn bước tiếp theo**, **điều kiện dừng**, **cách kiểm tra nghiệm/kết quả** và **ý nghĩa của phép đo** cho từng task.