const $ = id => document.getElementById(id);
async function unlock() {
  $("error").textContent = ""; $("open").disabled = true; $("open").textContent = "Checking…";
  try {
    const r = await fetch(`/api/notes/${encodeURIComponent(window.SECRET_TOKEN)}/read`, {
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({password:$("password").value})
    });
    const d = await r.json(); if (!r.ok) throw new Error(d.error || "Unable to open secret.");
    $("secret").textContent = d.message; $("secret").hidden = false;
    $("password").value = ""; $("password").disabled = true;
    $("open").hidden = true;
    document.querySelector(".muted").textContent = "This secret has been consumed. This page cannot reveal it again.";
  } catch(e) { $("error").textContent = e.message; }
  finally { if (!$("open").hidden) { $("open").disabled = false; $("open").innerHTML = 'Unlock secret <span>↗</span>'; } }
}
$("open").addEventListener("click", unlock);
$("password").addEventListener("keydown", e => { if (e.key === "Enter") unlock(); });
