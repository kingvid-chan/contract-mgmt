/* =============================================================
   Contract Management System — Global JS utilities
   ============================================================= */

// ---------- Modal ----------
let _modalCallback = null;

function showModal(title, body, confirmText, onConfirm) {
    const modal = document.getElementById('confirm-modal');
    modal.querySelector('.modal-title').textContent = title;
    modal.querySelector('.modal-body').textContent = body;
    const btn = document.getElementById('modal-confirm-btn');
    btn.textContent = confirmText || '确认';
    btn.className = 'btn btn-primary';
    _modalCallback = onConfirm;
    modal.style.display = 'flex';
}

function showDangerModal(title, body, confirmText, onConfirm) {
    showModal(title, body, confirmText || '删除', onConfirm);
    const btn = document.getElementById('modal-confirm-btn');
    btn.className = 'btn btn-danger';
}

function closeModal() {
    document.getElementById('confirm-modal').style.display = 'none';
    _modalCallback = null;
}

document.addEventListener('DOMContentLoaded', function () {
    const modalConfirm = document.getElementById('modal-confirm-btn');
    if (modalConfirm) {
        modalConfirm.addEventListener('click', function () {
            if (_modalCallback) { _modalCallback(); }
            closeModal();
        });
    }
    // Close modal on overlay click
    const overlay = document.querySelector('.modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeModal);
    }

    // Auto-dismiss flash messages
    document.querySelectorAll('.flash-message[data-auto-dismiss]').forEach(function (el) {
        setTimeout(function () {
            el.style.transition = 'opacity .3s';
            el.style.opacity = '0';
            setTimeout(function () { el.remove(); }, 300);
        }, 4000);
    });
});

// ---------- Logout ----------
function doLogout() {
    fetch('/projects/contract-mgmt/api/auth/logout', { method: 'POST' })
        .then(function () { window.location.href = '/projects/contract-mgmt/login'; })
        .catch(function () { window.location.href = '/projects/contract-mgmt/login'; });
}

// ---------- Delete confirmation (contract / attachment) ----------
function confirmDelete(url, itemName) {
    showDangerModal('确认删除', '确定要删除 ' + (itemName || '该项') + ' 吗？此操作不可撤销。', '删除', function () {
        fetch(url, { method: 'DELETE' })
            .then(function (r) {
                if (r.ok) { window.location.reload(); }
                else {
                    r.json().then(function (d) { alert(d.detail || '删除失败'); });
                }
            });
    });
}

// ---------- Status change confirmation ----------
function confirmStatusChange(url, newStatus, reasonId) {
    var reason = reasonId ? document.getElementById(reasonId).value : '';
    var body = JSON.stringify({ status: newStatus, reason: reason || null });
    showModal('确认操作', '确定要将合同状态变更为 ' + newStatus + ' 吗？', '确认', function () {
        fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body
        }).then(function (r) {
            if (r.ok) { window.location.reload(); }
            else {
                r.json().then(function (d) { alert(d.detail || '操作失败'); });
            }
        });
    });
}

// ---------- File upload preview ----------
function initUploadPreview(inputId, previewId) {
    var input = document.getElementById(inputId);
    if (!input) return;
    input.addEventListener('change', function () {
        var file = input.files[0];
        var preview = document.getElementById(previewId);
        if (!preview) return;
        if (!file) { preview.textContent = ''; return; }
        var sizeMB = (file.size / 1048576).toFixed(2);
        var ext = file.name.split('.').pop().toLowerCase();
        var allowed = ['pdf', 'doc', 'docx'];
        if (allowed.indexOf(ext) === -1) {
            preview.innerHTML = '<span style="color:#dc2626">不支持的文件类型，仅允许 PDF、DOC、DOCX</span>';
            input.value = '';
            return;
        }
        if (file.size > 10485760) {
            preview.innerHTML = '<span style="color:#dc2626">文件大小超过 10MB 限制</span>';
            input.value = '';
            return;
        }
        preview.textContent = file.name + ' (' + sizeMB + ' MB)';
    });
}

// ---------- Search debounce ----------
function debounce(fn, delay) {
    var timer = null;
    return function () {
        var ctx = this, args = arguments;
        clearTimeout(timer);
        timer = setTimeout(function () { fn.apply(ctx, args); }, delay);
    };
}

// ---------- Dynamic party rows (contract form) ----------
function addPartyRow(containerId) {
    var container = document.getElementById(containerId);
    var count = container.querySelectorAll('.party-row').length;
    if (count >= 10) return;
    var row = document.createElement('div');
    row.className = 'party-row form-row';
    row.innerHTML =
        '<div class="form-group">' +
        '<label class="form-label">签约方名称</label>' +
        '<input type="text" class="form-input" name="party_name_' + count + '" placeholder="公司/个人名称" required>' +
        '</div>' +
        '<div class="form-group">' +
        '<label class="form-label">角色</label>' +
        '<div style="display:flex;gap:8px;align-items:center;">' +
        '<input type="text" class="form-input" name="party_role_' + count + '" placeholder="如：甲方、乙方" required>' +
        '<button type="button" class="btn btn-sm btn-danger" onclick="this.closest(\'.party-row\').remove()">×</button>' +
        '</div>' +
        '</div>';
    container.appendChild(row);
}

// ---------- Form JSON builder (contract) ----------
function buildContractJSON(form) {
    var parties = [];
    var rows = form.querySelectorAll('.party-row');
    rows.forEach(function (row) {
        var nameInput = row.querySelector('input[name^="party_name_"]');
        var roleInput = row.querySelector('input[name^="party_role_"]');
        if (nameInput && roleInput && nameInput.value.trim() && roleInput.value.trim()) {
            parties.push({ name: nameInput.value.trim(), role: roleInput.value.trim() });
        }
    });
    return {
        title: form.querySelector('[name="title"]').value.trim(),
        contract_no: form.querySelector('[name="contract_no"]').value.trim(),
        parties: parties,
        amount: parseFloat(form.querySelector('[name="amount"]').value) || 0,
        sign_date: form.querySelector('[name="sign_date"]').value || null,
        expiry_date: form.querySelector('[name="expiry_date"]').value || null,
        content: form.querySelector('[name="content"]').value.trim() || null,
    };
}

// ---------- User form JSON builder ----------
function buildUserJSON(form, isCreate) {
    var data = {
        display_name: form.querySelector('[name="display_name"]').value.trim(),
        role: form.querySelector('[name="role"]').value,
    };
    if (isCreate) {
        data.username = form.querySelector('[name="username"]').value.trim();
        data.password = form.querySelector('[name="password"]').value;
    }
    return data;
}

// ---------- User toggle status ----------
function toggleUserStatus(userId) {
    fetch('/projects/contract-mgmt/api/users/' + userId + '/status', { method: 'PUT' })
        .then(function (r) {
            if (r.ok) { window.location.reload(); }
            else { r.json().then(function(d) { alert(d.detail); }); }
        });
}

// ---------- Form submit helpers ----------
function submitContractForm(form, url, method) {
    var data = buildContractJSON(form);
    if (!data.title) { alert('请输入合同标题'); return; }
    if (!data.contract_no) { alert('请输入合同编号'); return; }
    if (data.parties.length < 2) { alert('请至少填写两个签约方'); return; }
    if (data.amount < 0) { alert('金额不能为负数'); return; }

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    }).then(function (r) {
        if (r.ok) {
            r.json().then(function (d) {
                window.location.href = '/projects/contract-mgmt/contracts/' + d.id;
            });
        } else {
            r.json().then(function (d) { alert(d.detail || '操作失败'); });
        }
    });
    return false;
}

function submitUserForm(form, url, method, isCreate) {
    var data = buildUserJSON(form, isCreate);
    if (isCreate) {
        if (!data.username) { alert('请输入用户名'); return; }
        if (!data.password) { alert('请输入密码'); return; }
    }
    if (!data.display_name) { alert('请输入显示名'); return; }

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    }).then(function (r) {
        if (r.ok) {
            window.location.href = '/projects/contract-mgmt/users';
        } else {
            r.json().then(function (d) { alert(d.detail || '操作失败'); });
        }
    });
    return false;
}

function submitLoginForm(form) {
    var data = {
        username: form.querySelector('[name="username"]').value.trim(),
        password: form.querySelector('[name="password"]').value,
    };
    if (!data.username || !data.password) { alert('请输入用户名和密码'); return false; }
    var errorEl = document.getElementById('login-error');
    fetch('/projects/contract-mgmt/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    }).then(function (r) {
        if (r.ok) {
            var next = new URLSearchParams(window.location.search).get('next');
            window.location.href = next || '/projects/contract-mgmt/contracts';
        } else {
            r.json().then(function (d) {
                if (errorEl) { errorEl.textContent = d.detail; errorEl.style.display = 'block'; }
            });
        }
    });
    return false;
}

function submitPasswordForm(form) {
    var data = {
        old_password: form.querySelector('[name="old_password"]').value,
        new_password: form.querySelector('[name="new_password"]').value,
    };
    if (!data.old_password || !data.new_password) {
        alert('请填写完整');
        return false;
    }
    var errorEl = document.getElementById('password-error');
    fetch('/projects/contract-mgmt/api/users/me/password', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    }).then(function (r) {
        if (r.ok) {
            alert('密码修改成功');
            window.location.reload();
        } else {
            r.json().then(function (d) {
                if (errorEl) { errorEl.textContent = d.detail; errorEl.style.display = 'block'; }
            });
        }
    });
    return false;
}
