-- ============================================================
-- 002_seed_data.sql
-- Demo accounts and sample contracts (all fake data)
-- Passwords hashed with bcrypt (cost 12)
-- ============================================================

-- Demo accounts
-- admin / admin123
INSERT OR IGNORE INTO users (id, username, password_hash, display_name, role, is_active)
VALUES (1, 'admin', '$2b$12$pV2m7GBrLwT7ehERxk7LiecMqxoOK8Edp0YXg9H65v0reRwnZpcum', '管理员', 'admin', 1);

-- user / user123
INSERT OR IGNORE INTO users (id, username, password_hash, display_name, role, is_active)
VALUES (2, 'user', '$2b$12$jIxFTjo1t.MniXnZMd9uwuObl6E6/VSFRvARCE.Q5uNc2Umo3Hiay', '普通用户', 'user', 1);

-- Sample contracts (all fake data)
INSERT OR IGNORE INTO contracts (id, title, contract_no, parties, amount, status, sign_date, expiry_date, content, created_by)
VALUES (1, '2024年度办公用品采购合同', 'HT-2024-001',
        '[{"name": "恒通商贸有限公司", "role": "甲方"}, {"name": "瑞达办公用品供应中心", "role": "乙方"}]',
        150000.00, 'active', '2024-01-15', '2024-12-31',
        '第一条 采购内容：甲方委托乙方供应2024年度日常办公用品...', 1);

INSERT OR IGNORE INTO contracts (id, title, contract_no, parties, amount, status, sign_date, expiry_date, content, created_by)
VALUES (2, 'IT系统运维服务合同', 'HT-2024-002',
        '[{"name": "云帆科技有限公司", "role": "甲方"}, {"name": "中软信息技术服务有限公司", "role": "乙方"}]',
        480000.00, 'pending_review', null, '2025-06-30',
        '第一条 服务范围：乙方为甲方提供7×24小时IT系统运维技术支持...', 1);

INSERT OR IGNORE INTO contracts (id, title, contract_no, parties, amount, status, content, created_by)
VALUES (3, '会议室改造装修合同（草案）', 'HT-2025-001',
        '[{"name": "恒通商贸有限公司", "role": "甲方"}, {"name": "鹏程装饰工程有限公司", "role": "乙方"}]',
        320000.00, 'draft',
        '第一条 工程概况：对甲方办公楼3层A区会议室进行装修改造...', 2);
