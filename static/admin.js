const table = document.getElementById("studentsTable");

function cell(value) {
  return `<td>${value ?? "-"}</td>`;
}

async function loadAdminData() {
  const response = await fetch("/api/admin-data");
  if (!response.ok) return;
  const data = await response.json();

  document.getElementById("totalStudents").textContent = data.total_students;
  document.getElementById("engagedCount").textContent = data.counts.engaged;
  document.getElementById("neutralCount").textContent = data.counts.neutral;
  document.getElementById("disengagedCount").textContent = data.counts.disengaged;
  document.getElementById("classScore").textContent = `${Number(data.class_score).toFixed(1)}%`;

  table.innerHTML = data.students.map(student => `
    <tr>
      ${cell(student.student_name)}
      ${cell(student.roll_number)}
      ${cell(student.branch)}
      ${cell(student.phone)}
      ${cell(student.email)}
      ${cell(student.login_status)}
      ${cell(student.current_status)}
      ${cell(student.confidence)}
      ${cell(student.detected_frames)}
      ${cell(student.total_checks)}
      ${cell(student.engaged_checks)}
      ${cell(student.neutral_checks)}
      ${cell(student.disengaged_checks)}
      ${cell(student.attention_score)}
      ${cell(student.final_outcome)}
      ${cell(student.last_updated)}
      ${cell(student.logged_in_at)}
      ${cell(student.logged_out_at)}
    </tr>
  `).join("");
}

document.getElementById("resetBtn").addEventListener("click", async () => {
  if (!confirm("Reset current class session data?")) return;
  await fetch("/api/reset", { method: "POST" });
  loadAdminData();
});

loadAdminData();
setInterval(loadAdminData, 3000);
