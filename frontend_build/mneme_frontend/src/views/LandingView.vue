<template>
  <main class="landing-page">
    <section class="hero">
      <div class="hero__copy">
        <p class="section-header__eyebrow">Mneme Frontend / Vue 3</p>
        <h1>把个人内容库，变成可追溯、可分析、可陪伴的记忆工作台。</h1>
        <p>
          这个前端面向当前 Mneme
          后端的稳定主链路设计：认证、知识库、文档上传与索引、RAG
          问答、记忆库、画像与成长分析。
        </p>
        <div class="hero__actions">
          <RouterLink class="primary-button" :to="{ name: 'login' }">进入工作台</RouterLink>
          <RouterLink class="ghost-button" :to="{ name: 'register' }">创建账号</RouterLink>
        </div>
      </div>

      <div class="hero__panel">
        <div class="hero-card hero-card--accent">
          <span>01</span>
          <strong>上传与索引</strong>
          <p>让散落的写作、访谈、笔记进入可检索状态。</p>
        </div>
        <div class="hero-card">
          <span>02</span>
          <strong>问答与溯源</strong>
          <p>每次回答都展示 chunk 来源，避免只给结论不见证据。</p>
        </div>
        <div class="hero-card">
          <span>03</span>
          <strong>记忆与洞察</strong>
          <p>把内容增长轨迹从“堆文档”推进到“看主题、看变化、看自己”。</p>
        </div>
      </div>
    </section>
  </main>
</template>
