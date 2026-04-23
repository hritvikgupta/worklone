import React from 'react';
import './AgentsSection.css';

export function AgentsSection() {
  return (
    <section className="agents-showcase" aria-label="Agents section">
      <div className="wrap">
        <h2 className="title">
          Deploy every kind of AI agent in your workspace <em>in one click.</em>
        </h2>

        <div className="grid">
          <article className="card">
            <div className="code-bg">
              <span className="c">// research.agent.ts</span>{'\n'}
              <span className="k">import</span> {'{ Agent }'} <span className="k">from</span> <span className="s">'@core/agents'</span>{'\n'}
              <span className="k">import</span> {'{ corpus }'} <span className="k">from</span> <span className="s">'./corpus'</span>{'\n\n'}
              <span className="k">const</span> research = <span className="k">new</span> Agent({`{`}{'\n'}
              {'  '}role: <span className="s">'researcher'</span>,{`\n`}
              {'  '}tools: [<span className="s">'search'</span>, <span className="s">'cite'</span>],{`\n`}
              {'  '}memory: corpus.index,{`\n`}
              {`})\n\n`}
              <span className="k">await</span> research.run({`{`}{'\n'}
              {'  '}query: <span className="s">'Q3 revenue drivers'</span>,{`\n`}
              {'  '}depth: <span className="s">'exhaustive'</span>,{`\n`}
              {`})`}
            </div>
            <div className="card-head">
              <div className="tag">01 · Research</div>
              <h3>Research Agent</h3>
              <p>Reads across your knowledge base, extracts the salient passages, and returns cited answers in seconds.</p>
              <div className="open" aria-hidden="true">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 9L9 3M9 3H4M9 3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <div className="art">
              <div className="doc">
                <div className="doc-head">
                  <div className="doc-dot" />
                  <div className="doc-dot" />
                  <div className="doc-dot" />
                  <div className="doc-title">q3_earnings_memo.pdf · p.4</div>
                </div>
                <div className="doc-h">Drivers of Q3 revenue</div>
                <p className="doc-p">Growth was concentrated in enterprise, where <span className="hl">net new ARR rose 38% QoQ</span>, offsetting softer self-serve.</p>
                <p className="doc-p"><span className="hl d2">EMEA expansion contributed $4.2M</span>, led by the Frankfurt and Madrid offices opening in July.</p>
                <p className="doc-p">Gross margin held at 74% despite <span className="hl d3">inference costs climbing 12%</span> after the model upgrade.</p>
                <div className="doc-cite">↳ 3 citations · memo_q3.pdf, board_deck.pptx</div>
                <div className="cursor c1" />
              </div>
            </div>
          </article>

          <article className="card">
            <div className="code-bg">
              <span className="c">// web.agent.ts</span>{'\n'}
              <span className="k">import</span> {'{ Agent }'} <span className="k">from</span> <span className="s">'@core/agents'</span>{'\n'}
              <span className="k">import</span> {'{ browser }'} <span className="k">from</span> <span className="s">'./headless'</span>{'\n\n'}
              <span className="k">const</span> web = <span className="k">new</span> Agent({`{`}{'\n'}
              {'  '}role: <span className="s">'browser'</span>,{`\n`}
              {'  '}tools: [<span className="s">'click'</span>, <span className="s">'fill'</span>, <span className="s">'scrape'</span>],{`\n`}
              {'  '}session: browser.persist,{`\n`}
              {`})\n\n`}
              <span className="k">await</span> web.goto(<span className="s">'docs.ai/pricing'</span>){'\n'}
              <span className="k">const</span> plan = <span className="k">await</span> web.extract({'\n'}
              {'  '}<span className="s">'the enterprise tier'</span>{'\n'})
            </div>
            <div className="card-head">
              <div className="tag">02 · Browsing</div>
              <h3>Web Agent</h3>
              <p>Navigates sites like a human — clicks, forms, scroll — and pulls structured data from messy pages.</p>
              <div className="open" aria-hidden="true">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 9L9 3M9 3H4M9 3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <div className="art">
              <div className="browser">
                <div className="b-bar">
                  <div className="b-dot" />
                  <div className="b-dot" />
                  <div className="b-dot" />
                  <div className="b-url"><span className="urltext">google.com/search?q=enterprise+SSO+pricing</span></div>
                </div>
                <div className="b-body">
                  <div className="b-search">3 results · <b>&quot;enterprise SSO pricing&quot;</b></div>
                  <div className="b-result">
                    <div className="r-title">Pricing — Plans &amp; tiers</div>
                    <div className="r-desc">Starter, Team, and Enterprise. SSO included from Team up.</div>
                  </div>
                  <div className="b-result hit">
                    <div className="r-title">Enterprise · SAML, SCIM, audit logs</div>
                    <div className="r-desc">Custom pricing. 99.99% SLA. Dedicated success manager.</div>
                  </div>
                  <div className="ripple" />
                  <div className="cursor c2" />
                </div>
              </div>
            </div>
          </article>

          <article className="card">
            <div className="code-bg">
              <span className="c">// data.agent.ts</span>{'\n'}
              <span className="k">import</span> {'{ Agent }'} <span className="k">from</span> <span className="s">'@core/agents'</span>{'\n'}
              <span className="k">import</span> {'{ warehouse }'} <span className="k">from</span> <span className="s">'./db'</span>{'\n\n'}
              <span className="k">const</span> analyst = <span className="k">new</span> Agent({`{`}{'\n'}
              {'  '}role: <span className="s">'analyst'</span>,{`\n`}
              {'  '}tools: [<span className="s">'sql'</span>, <span className="s">'chart'</span>, <span className="s">'pandas'</span>],{`\n`}
              {'  '}datasets: warehouse.all(),{`\n`}
              {`})\n\n`}
              <span className="k">const</span> report = <span className="k">await</span> analyst.ask({'\n'}
              {'  '}<span className="s">'Weekly cohort retention?'</span>{'\n'})
            </div>
            <div className="card-head">
              <div className="tag">03 · Analysis</div>
              <h3>Data Agent</h3>
              <p>Queries your warehouse, runs the numbers, and hands back charts with plain-language takeaways.</p>
              <div className="open" aria-hidden="true">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 9L9 3M9 3H4M9 3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <div className="art">
              <div className="chart">
                <div className="chart-head">
                  <div>
                    <div className="chart-label">Weekly retention · cohort wk0</div>
                    <div className="chart-val">64.2%<span className="trend">+4.1 pts</span></div>
                  </div>
                </div>
                <svg className="chart-svg" viewBox="0 0 240 88" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="oklch(0.58 0.14 262)" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="oklch(0.58 0.14 262)" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <line x1="0" y1="22" x2="240" y2="22" stroke="#f0f0f2" strokeWidth="1" strokeDasharray="2 3" />
                  <line x1="0" y1="50" x2="240" y2="50" stroke="#f0f0f2" strokeWidth="1" strokeDasharray="2 3" />
                  <path className="chart-fill" d="M0,70 L20,62 L45,68 L70,50 L95,54 L120,40 L145,44 L170,28 L195,32 L220,18 L240,14 L240,88 L0,88 Z" />
                  <path className="chart-path" d="M0,70 L20,62 L45,68 L70,50 L95,54 L120,40 L145,44 L170,28 L195,32 L220,18 L240,14" />
                  <circle className="chart-dot" cx="240" cy="14" r="3" />
                </svg>
                <div className="chart-xaxis">
                  <span>W1</span><span>W3</span><span>W5</span><span>W7</span><span>W9</span><span>W11</span>
                </div>
                <div className="chart-takeaway"><b>Takeaway:</b> onboarding v2 lifted week-4 retention most — enterprise cohorts now curve up.</div>
              </div>
            </div>
          </article>

          <article className="card">
            <div className="code-bg">
              <span className="c">// code.agent.ts</span>{'\n'}
              <span className="k">import</span> {'{ Agent }'} <span className="k">from</span> <span className="s">'@core/agents'</span>{'\n'}
              <span className="k">import</span> {'{ repo }'} <span className="k">from</span> <span className="s">'./git'</span>{'\n\n'}
              <span className="k">const</span> coder = <span className="k">new</span> Agent({`{`}{'\n'}
              {'  '}role: <span className="s">'engineer'</span>,{`\n`}
              {'  '}tools: [<span className="s">'edit'</span>, <span className="s">'test'</span>, <span className="s">'commit'</span>],{`\n`}
              {'  '}context: repo.tree(),{`\n`}
              {`})\n\n`}
              <span className="k">await</span> coder.run({`{`}{'\n'}
              {'  '}task: <span className="s">'add rate limiter'</span>,{`\n`}
              {`})`}
            </div>
            <div className="card-head">
              <div className="tag">04 · Engineering</div>
              <h3>Code Agent</h3>
              <p>Ships pull requests — writes, tests, reviews, and iterates until the build turns green.</p>
              <div className="open" aria-hidden="true">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 9L9 3M9 3H4M9 3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <div className="art">
              <div className="editor">
                <div className="ed-head">
                  <div className="ed-tab">rate-limiter.ts</div>
                  <div className="ed-tab muted-tab">server.ts</div>
                  <div className="ed-tab muted-tab">limiter.test.ts</div>
                </div>
                <div className="ed-body">
                  <div className="ed-line"><span className="muted">12</span>  <span className="kw">export function</span> <span className="fn">limit</span>(req: Request) {'{'}</div>
                  <div className="ed-line"><span className="muted">13</span>    <span className="kw">const</span> key = req.headers.<span className="fn">get</span>(<span className="str">'x-api-key'</span>)<span className="caret" /></div>
                  <div className="ed-line"><span className="muted">14</span>    <span className="kw">if</span> (!bucket.<span className="fn">take</span>(key, <span className="str">100</span>)) {'{'}</div>
                  <div className="ed-line"><span className="muted">15</span>      <span className="kw">throw new</span> <span className="fn">TooMany</span>(<span className="str">'60s'</span>)</div>
                  <div className="ed-line"><span className="muted">16</span>    {'}'}</div>
                  <div className="ed-line"><span className="muted">17</span>  {'}'}</div>
                  <div className="suggest"><span className="pill">AI</span>bucket.take(key, 100)</div>
                </div>
              </div>
            </div>
          </article>

          <article className="card">
            <div className="code-bg">
              <span className="c">// inbox.agent.ts</span>{'\n'}
              <span className="k">import</span> {'{ Agent }'} <span className="k">from</span> <span className="s">'@core/agents'</span>{'\n'}
              <span className="k">import</span> {'{ inbox }'} <span className="k">from</span> <span className="s">'./mail'</span>{'\n\n'}
              <span className="k">const</span> writer = <span className="k">new</span> Agent({`{`}{'\n'}
              {'  '}role: <span className="s">'correspondent'</span>,{`\n`}
              {'  '}tools: [<span className="s">'draft'</span>, <span className="s">'send'</span>, <span className="s">'triage'</span>],{`\n`}
              {'  '}voice: <span className="s">'warm, concise'</span>,{`\n`}
              {`})\n\n`}
              <span className="k">await</span> writer.reply(inbox.latest, {`{`}{'\n'}
              {'  '}tone: <span className="s">'professional'</span>,{`\n`}
              {`})`}
            </div>
            <div className="card-head">
              <div className="tag">05 · Inbox</div>
              <h3>Inbox Agent</h3>
              <p>Triages mail, drafts replies in your voice, and quietly clears the queue while you&apos;re in focus.</p>
              <div className="open" aria-hidden="true">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 9L9 3M9 3H4M9 3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <div className="art">
              <div className="mail">
                <div className="m-head">
                  <div className="m-avatar">PK</div>
                  <div>
                    <div className="m-from">Re: Intro call next week</div>
                    <div className="m-sub">to [email protected] · Mon 9:14am</div>
                  </div>
                </div>
                <div className="m-body">
                  <div className="m-type"><span className="m-reveal">Hi Priya — thanks for the note. Tuesday at 11 works on my end. I&apos;ll send a calendar hold with the Zoom link shortly. Looking forward to it.</span></div>
                  <div className="send-btn">Send ↵</div>
                </div>
              </div>
            </div>
          </article>

          <article className="card">
            <div className="code-bg">
              <span className="c">// plan.agent.ts</span>{'\n'}
              <span className="k">import</span> {'{ Agent }'} <span className="k">from</span> <span className="s">'@core/agents'</span>{'\n'}
              <span className="k">import</span> {'{ cal }'} <span className="k">from</span> <span className="s">'./calendar'</span>{'\n\n'}
              <span className="k">const</span> planner = <span className="k">new</span> Agent({`{`}{'\n'}
              {'  '}role: <span className="s">'scheduler'</span>,{`\n`}
              {'  '}tools: [<span className="s">'book'</span>, <span className="s">'move'</span>, <span className="s">'rsvp'</span>],{`\n`}
              {'  '}window: cal.twoWeeks,{`\n`}
              {`})\n\n`}
              <span className="k">await</span> planner.find({`{`}{'\n'}
              {'  '}invitees: team,{`\n`}
              {'  '}duration: <span className="s">'45m'</span>,{`\n`}
              {`})`}
            </div>
            <div className="card-head">
              <div className="tag">06 · Planning</div>
              <h3>Scheduler Agent</h3>
              <p>Negotiates calendars across timezones, books rooms, and rebalances the week when meetings slip.</p>
              <div className="open" aria-hidden="true">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M3 9L9 3M9 3H4M9 3V8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                </svg>
              </div>
            </div>
            <div className="art">
              <div className="cal">
                <div className="cal-head">
                  <div className="cal-month">Apr 27 — May 1</div>
                  <div className="cal-nav">‹  ›</div>
                </div>
                <div className="cal-grid">
                  <div className="cal-time" />
                  <div className="cal-day">M</div><div className="cal-day today">T</div><div className="cal-day">W</div><div className="cal-day">T</div><div className="cal-day">F</div>

                  <div className="cal-time">9</div>
                  <div className="cal-cell" />
                  <div className="cal-cell"><div className="cal-ev a">Standup</div></div>
                  <div className="cal-cell" />
                  <div className="cal-cell" />
                  <div className="cal-cell"><div className="cal-ev b">1:1 Priya</div></div>

                  <div className="cal-time">11</div>
                  <div className="cal-cell"><div className="cal-ev c">Design rvw</div></div>
                  <div className="cal-cell" />
                  <div className="cal-cell"><div className="cal-ev d">Intro · ACME</div></div>
                  <div className="cal-cell"><div className="cal-ev e">QBR prep</div></div>
                  <div className="cal-cell" />

                  <div className="cal-time">1</div>
                  <div className="cal-cell" />
                  <div className="cal-cell"><div className="cal-ev b">Lunch · Sam</div></div>
                  <div className="cal-cell" />
                  <div className="cal-cell"><div className="cal-ev a">Board sync</div></div>
                  <div className="cal-cell" />

                  <div className="cal-time">3</div>
                  <div className="cal-cell"><div className="cal-ev c">Focus</div></div>
                  <div className="cal-cell" />
                  <div className="cal-cell"><div className="cal-ev e">Hiring loop</div></div>
                  <div className="cal-cell" />
                  <div className="cal-cell"><div className="cal-ev d">Ship review</div></div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    </section>
  );
}
