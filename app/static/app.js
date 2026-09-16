const API = "";

const STATUS_LABELS = {
  assistido: "Assistido",
  assistindo: "Assistindo",
  dropado: "Dropado",
  quero_assistir: "Quero assistir",
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---------- Chat "Bem-vindo" (Fase 4) ----------
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSubmit = document.getElementById("chat-submit");

function adicionarMensagem(html, classe) {
  const div = document.createElement("div");
  div.className = `chat-msg ${classe}`;
  div.innerHTML = html;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function renderizarResposta(resposta) {
  if (!resposta.itens.length) {
    return `
      <div class="rec-observacao">${escapeHtml(resposta.observacao || "Não encontrei nada que combinasse bem com esse pedido no catálogo atual.")}</div>
    `;
  }
  const observacao = resposta.observacao
    ? `<div class="rec-observacao">${escapeHtml(resposta.observacao)}</div>`
    : "";
  const itens = resposta.itens
    .map(
      (item) => `
        <div class="rec-item">
          <div class="rec-item-title">${escapeHtml(item.titulo)}</div>
          <div class="rec-item-just">${escapeHtml(item.justificativa)}</div>
        </div>
      `
    )
    .join("");
  return observacao + itens;
}

chatForm.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const mensagem = chatInput.value.trim();
  if (!mensagem) return;

  adicionarMensagem(escapeHtml(mensagem), "chat-msg--user");
  chatInput.value = "";
  chatInput.disabled = true;
  chatSubmit.disabled = true;

  const msgCarregando = adicionarMensagem("Pensando...", "chat-msg--bot chat-msg--loading");

  try {
    const res = await fetch(`${API}/recomendacao/pedido`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem, top_n: 5 }),
    });

    if (!res.ok) {
      const erro = await res.json().catch(() => ({}));
      msgCarregando.className = "chat-msg chat-msg--erro";
      msgCarregando.textContent =
        erro.detail || "Não consegui gerar uma recomendação agora. Tente de novo.";
      return;
    }

    const resposta = await res.json();
    msgCarregando.className = "chat-msg chat-msg--bot";
    msgCarregando.innerHTML = renderizarResposta(resposta);
  } catch (err) {
    msgCarregando.className = "chat-msg chat-msg--erro";
    msgCarregando.textContent = "Erro de conexão com o servidor.";
    console.error(err);
  } finally {
    chatInput.disabled = false;
    chatSubmit.disabled = false;
    chatInput.focus();
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
});

// ---------- Lista "Já assistidos" ----------
const grid = document.getElementById("grid");
const listaStatus = document.getElementById("lista-status");

async function carregarAnimes() {
  listaStatus.textContent = "Carregando...";
  try {
    const res = await fetch(`${API}/animes`);
    if (!res.ok) throw new Error("Falha ao carregar lista");
    const animes = await res.json();
    renderGrid(animes);
    listaStatus.textContent = animes.length
      ? `${animes.length} anime(s) cadastrado(s)`
      : "";
  } catch (err) {
    listaStatus.textContent = "Erro ao carregar lista.";
    console.error(err);
  }
}

function renderGrid(animes) {
  if (!animes.length) {
    grid.innerHTML = `<div class="empty-state">Nenhum anime cadastrado ainda. Clique em "Adicionar anime" para começar.</div>`;
    return;
  }
  grid.innerHTML = animes.map(renderCard).join("");

  animes.forEach((anime) => {
    document
      .getElementById(`btn-edit-${anime.id}`)
      .addEventListener("click", () => toggleEdit(anime.id));
    document
      .getElementById(`btn-delete-${anime.id}`)
      .addEventListener("click", () => deletarAnime(anime.id));
    document
      .getElementById(`edit-form-${anime.id}`)
      .addEventListener("submit", (ev) => salvarEdicao(ev, anime.id));
  });
}

function renderCard(anime) {
  const generos = (anime.tags_anilist || []).slice(0, 5);
  const notasProprias = anime.tags_proprias || [];
  return `
    <div class="card" id="card-${anime.id}">
      <div class="card-header">
        <p class="card-title">${escapeHtml(anime.titulo)}</p>
        <span class="badge badge-${anime.status}">${STATUS_LABELS[anime.status] ?? anime.status}</span>
      </div>
      <div class="card-nota">${anime.nota != null ? `Nota: ${anime.nota}/10` : "Sem nota"}</div>
      ${
        generos.length
          ? `<div class="tag-group">
               <span class="tag-group-label">Gêneros</span>
               <div class="card-tags">
                 ${generos.map((t) => `<span class="tag-pill">${escapeHtml(t)}</span>`).join("")}
               </div>
             </div>`
          : ""
      }
      ${
        notasProprias.length
          ? `<div class="tag-group">
               <span class="tag-group-label">Minhas notas</span>
               <div class="card-tags">
                 ${notasProprias.map((t) => `<span class="tag-pill tag-pill--nota">${escapeHtml(t)}</span>`).join("")}
               </div>
             </div>`
          : ""
      }
      <div class="card-actions">
        <button class="btn btn-secondary" id="btn-edit-${anime.id}">Editar</button>
        <button class="btn btn-danger" id="btn-delete-${anime.id}">Remover</button>
      </div>
      <form class="edit-form" id="edit-form-${anime.id}">
        <label>
          Status
          <select name="status">
            ${Object.entries(STATUS_LABELS)
              .map(
                ([value, label]) =>
                  `<option value="${value}" ${value === anime.status ? "selected" : ""}>${label}</option>`
              )
              .join("")}
          </select>
        </label>
        <label>
          Nota (0-10)
          <input type="number" name="nota" min="0" max="10" value="${anime.nota ?? ""}" />
        </label>
        <label>
          Tags próprias (separadas por vírgula)
          <input type="text" name="tags_proprias" value="${escapeHtml((anime.tags_proprias || []).join(", "))}" />
        </label>
        <div class="dialog-actions">
          <button type="submit" class="btn btn-primary">Salvar</button>
        </div>
      </form>
    </div>
  `;
}

function toggleEdit(id) {
  document.getElementById(`edit-form-${id}`).classList.toggle("open");
}

async function salvarEdicao(ev, id) {
  ev.preventDefault();
  const form = ev.target;
  const status = form.status.value;
  const notaRaw = form.nota.value;
  const tags = form.tags_proprias.value
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const body = {
    status,
    nota: notaRaw === "" ? null : Number(notaRaw),
    tags_proprias: tags,
  };

  try {
    const res = await fetch(`${API}/animes/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Falha ao salvar");
    await carregarAnimes();
  } catch (err) {
    alert("Não foi possível salvar as alterações.");
    console.error(err);
  }
}

async function deletarAnime(id) {
  if (!confirm("Remover este anime da lista?")) return;
  try {
    const res = await fetch(`${API}/animes/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Falha ao remover");
    await carregarAnimes();
  } catch (err) {
    alert("Não foi possível remover.");
    console.error(err);
  }
}

// ---------- Dialog: buscar + cadastrar ----------
const dialog = document.getElementById("dialog-add");
const formSearch = document.getElementById("form-search");
const formRegister = document.getElementById("form-register");
const searchResults = document.getElementById("search-results");

document.getElementById("btn-add").addEventListener("click", () => {
  formSearch.reset();
  formSearch.classList.remove("hidden");
  formRegister.classList.add("hidden");
  searchResults.innerHTML = "";
  dialog.showModal();
});

document.getElementById("btn-close-dialog").addEventListener("click", () => dialog.close());
document.getElementById("btn-back-search").addEventListener("click", () => {
  formRegister.classList.add("hidden");
  formSearch.classList.remove("hidden");
});

formSearch.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const query = document.getElementById("input-query").value.trim();
  if (!query) return;

  searchResults.innerHTML = `<div class="muted">Buscando...</div>`;
  try {
    const res = await fetch(`${API}/animes/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    if (!res.ok) throw new Error("Falha na busca");
    const resultados = await res.json();
    renderSearchResults(resultados);
  } catch (err) {
    searchResults.innerHTML = `<div class="muted">Erro ao buscar na AniList.</div>`;
    console.error(err);
  }
});

function renderSearchResults(resultados) {
  if (!resultados.length) {
    searchResults.innerHTML = `<div class="muted">Nenhum resultado encontrado.</div>`;
    return;
  }
  searchResults.innerHTML = resultados
    .map(
      (r, idx) => `
      <div class="result-item" data-idx="${idx}">
        <span>${escapeHtml(r.titulo)}</span>
        <span class="result-meta">${r.ano ?? "?"} · ${escapeHtml(r.formato ?? "")}</span>
      </div>
    `
    )
    .join("");

  searchResults.querySelectorAll(".result-item").forEach((el) => {
    el.addEventListener("click", () => abrirFormRegistro(resultados[Number(el.dataset.idx)]));
  });
}

function abrirFormRegistro(resultado) {
  document.getElementById("register-title").textContent = `Cadastrar: ${resultado.titulo}`;
  document.getElementById("reg-anilist-id").value = resultado.anilist_id;
  document.getElementById("reg-status").value = "assistido";
  document.getElementById("reg-nota").value = "";
  document.getElementById("reg-tags").value = "";
  formSearch.classList.add("hidden");
  formRegister.classList.remove("hidden");
}

formRegister.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const anilistId = Number(document.getElementById("reg-anilist-id").value);
  const status = document.getElementById("reg-status").value;
  const notaRaw = document.getElementById("reg-nota").value;
  const tags = document
    .getElementById("reg-tags")
    .value.split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  const body = {
    anilist_id: anilistId,
    status,
    nota: notaRaw === "" ? null : Number(notaRaw),
    tags_proprias: tags,
  };

  try {
    const res = await fetch(`${API}/animes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (res.status === 409) {
      alert("Esse anime já está cadastrado.");
      return;
    }
    if (!res.ok) throw new Error("Falha ao cadastrar");
    dialog.close();
    await carregarAnimes();
  } catch (err) {
    alert("Não foi possível cadastrar o anime.");
    console.error(err);
  }
});

carregarAnimes();
