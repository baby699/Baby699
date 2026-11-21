const $ = id => document.getElementById(id);
$("create").addEventListener("click", async () => {
  $("error").textContent = ""; $("result").hidden = true;
  const message = $("message").value, password = $("password").value;
  if (!message.trim() || !password) { $("error").textContent = "Enter a message and password."; return; }
  $("create").disabled = true; $("create").textContent = "Creating…";
  try {
    const r = await fetch("/api/notes", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message,password})});
    const d = await r.json(); if (!r.ok) throw new Error(d.error || "Could not create link.");
    const full = new URL(d.url, location.href).href;
    $("link").value = full; $("result").hidden = false;
  } catch(e) { $("error").textContent = e.message; }
  finally { $("create").disabled = false; $("create").innerHTML = 'Create one-time link <span>↗</span>'; }
});
$("copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("link").value); $("copy").textContent = "Copied"; }
  catch { $("link").select(); document.execCommand("copy"); $("copy").textContent = "Copied"; }
});
