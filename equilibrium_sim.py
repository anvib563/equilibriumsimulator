import streamlit as st
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # ✅ ELIMINATES ALL ScriptRunContext WARNINGS
import matplotlib.pyplot as plt
import random

# ==========================================
# 1. THE MATH: Gini Coefficient & Analytics
# ==========================================

def calculate_gini(wealth_list):
    """
    Calculates the Gini Coefficient (0 = perfect equality, 1 = perfect inequality).
    """
    wealth = np.array(wealth_list)
    if len(wealth) == 0 or np.sum(wealth) == 0:
        return 0.0
    
    sorted_wealth = np.sort(wealth)
    n = len(sorted_wealth)
    index = np.arange(1, n + 1)
    
    gini = (2 * np.sum(index * sorted_wealth)) / (n * np.sum(sorted_wealth)) - (n + 1) / n
    return round(gini, 4)

def generate_lorenz_data(wealth_list):
    """
    Prepares data for the Lorenz Curve.
    """
    wealth = np.array(sorted(wealth_list))
    n = len(wealth)
    if n == 0 or np.sum(wealth) == 0:
        return np.array([]), np.array([])
    
    cum_wealth = np.cumsum(wealth)
    cum_pop = np.arange(1, n + 1) / n
    cum_wealth_pct = cum_wealth / np.sum(wealth)
    
    return cum_pop, cum_wealth_pct

# ==========================================
# 2. THE AGENT: The People
# ==========================================

class Agent:
    def __init__(self, agent_id, agent_type, grid_pos):
        self.id = agent_id
        self.type = agent_type
        self.wealth = 1000
        self.x, self.y = grid_pos
        self.is_alive = True

    def trade(self, neighbor, transaction_cost=0.001):
        if not self.is_alive or not neighbor.is_alive:
            return

        if self.type == 'spender':
            trade_amount = random.uniform(10, 100)
        elif self.type == 'saver':
            if self.wealth < 500:
                return
            trade_amount = random.uniform(5, 50)
        else: 
            trade_amount = random.uniform(20, 200)

        if random.random() > 0.5:
            payer, receiver = self, neighbor
        else:
            payer, receiver = neighbor, self

        if payer.wealth >= trade_amount:
            fee = trade_amount * transaction_cost
            payer.wealth -= (trade_amount + fee)
            receiver.wealth += trade_amount

    def invest(self, interest_rate=0.05):
        if self.type == 'investor' and self.wealth > 0:
            growth = self.wealth * interest_rate
            self.wealth += growth

    def save(self, threshold=500):
        if self.type == 'saver' and self.wealth < threshold:
            return True
        return False

    def reset(self, inheritance_tax_rate=0.0):
        if self.wealth > 0:
            tax = self.wealth * inheritance_tax_rate
            self.wealth = (self.wealth - tax) / 2
        else:
            self.wealth = 100

# ==========================================
# 3. THE SIMULATION: The Engine
# ==========================================

class Economy:
    def __init__(self, n_agents=100, grid_size=10):
        self.n_agents = n_agents
        self.grid_size = grid_size
        self.agents = []
        self.turn = 0
        self.data_log = []
        self.init_agents()

    def init_agents(self):
        self.agents = []
        for i in range(self.n_agents):
            r = random.random()
            if r < 0.4:
                atype = 'spender'
            elif r < 0.7:
                atype = 'saver'
            else:
                atype = 'investor'
            
            pos = (random.randint(0, self.grid_size-1), random.randint(0, self.grid_size-1))
            self.agents.append(Agent(i, atype, pos))

    def get_neighbors(self, agent):
        neighbors = []
        for other in self.agents:
            if other.id == agent.id:
                continue
            dist = abs(agent.x - other.x) + abs(agent.y - other.y)
            if dist == 1:
                neighbors.append(other)
        return neighbors

    def run_turn(self, policy_config):
        self.turn += 1
        
        if policy_config.get('ubi', False):
            for agent in self.agents:
                agent.wealth += policy_config.get('ubi_amount', 0)

        for agent in self.agents:
            agent.invest()

        for agent in self.agents:
            if not agent.is_alive:
                continue
            neighbors = self.get_neighbors(agent)
            if neighbors:
                neighbor = random.choice(neighbors)
                if agent.save():
                    continue
                agent.trade(neighbor, transaction_cost=policy_config.get('transaction_cost', 0.001))

        if self.turn % 50 == 0:
            self.apply_progressive_tax(policy_config.get('tax_rate', 0))
            self.apply_inheritance_tax(policy_config.get('inheritance_tax', 0))

        wealths = [a.wealth for a in self.agents]
        gini = calculate_gini(wealths)
        bankrupt = sum(1 for w in wealths if w <= 0)
        
        self.data_log.append({
            'turn': self.turn,
            'gini': gini,
            'avg_wealth': np.mean(wealths),
            'bankrupt_count': bankrupt
        })

    def apply_progressive_tax(self, tax_rate):
        if tax_rate <= 0:
            return
        sorted_agents = sorted(self.agents, key=lambda x: x.wealth, reverse=True)
        top_5_count = max(1, int(len(sorted_agents) * 0.05))
        bottom_20_count = max(1, int(len(sorted_agents) * 0.20))
        
        tax_collected = 0
        for agent in sorted_agents[:top_5_count]:
            tax = agent.wealth * tax_rate
            tax_collected += tax
            agent.wealth -= tax
        
        bottom_agents = sorted_agents[-bottom_20_count:]
        if bottom_20_count > 0:
            share = tax_collected / bottom_20_count
            for agent in bottom_agents:
                agent.wealth += share

    def apply_inheritance_tax(self, tax_rate):
        if tax_rate <= 0:
            return
        for agent in self.agents:
            if agent.wealth <= 0:
                agent.reset(inheritance_tax_rate=tax_rate)

    def trigger_black_swan(self, impact=0.3):
        for agent in self.agents:
            if agent.wealth > 0:
                agent.wealth *= (1 - impact)
        
        wealths = [a.wealth for a in self.agents]
        gini = calculate_gini(wealths)
        bankrupt = sum(1 for w in wealths if w <= 0)
        
        self.data_log.append({
            'turn': self.turn,
            'gini': gini,
            'avg_wealth': np.mean(wealths),
            'bankrupt_count': bankrupt,
            'event': 'Black Swan'
        })

# ==========================================
# 4. THE DASHBOARD: Streamlit UI
# ==========================================

st.set_page_config(page_title="Equilibrium Simulator", layout="wide")

# --- Initialize session state defaults ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.economy = None
    st.session_state.last_n_agents = 100
    st.session_state.last_grid_size = 10

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Policy & Parameters")

n_agents = st.sidebar.slider("Number of Agents", 50, 500, 100)
grid_size = st.sidebar.slider("Grid Size (Local Economy)", 5, 20, 10)

st.sidebar.subheader("Market Friction")
transaction_cost = st.sidebar.slider("Transaction Cost (%)", 0.0, 0.05, 0.001, 0.0001)

st.sidebar.subheader("Government Policy")
ubi_enabled = st.sidebar.checkbox("Universal Basic Income (UBI)", value=False)
ubi_amount = st.sidebar.number_input("UBI Amount / Turn", 0.0, 100.0, 1.0, step=0.5)

tax_enabled = st.sidebar.checkbox("Progressive Tax (Every 50 Turns)", value=False)
tax_rate = st.sidebar.slider("Tax Rate on Top 5%", 0.0, 0.5, 0.1)

inheritance_enabled = st.sidebar.checkbox("Inheritance Tax (On Reset)", value=False)
inheritance_tax = st.sidebar.slider("Inheritance Tax Rate", 0.0, 0.5, 0.2)

# --- Initialize or update economy ---
if st.session_state.economy is None:
    st.session_state.economy = Economy(n_agents=n_agents, grid_size=grid_size)
    st.session_state.last_n_agents = n_agents
    st.session_state.last_grid_size = grid_size

needs_reset = (n_agents != st.session_state.last_n_agents or 
               grid_size != st.session_state.last_grid_size)
if needs_reset:
    st.session_state.economy = Economy(n_agents=n_agents, grid_size=grid_size)
    st.session_state.last_n_agents = n_agents
    st.session_state.last_grid_size = grid_size

economy = st.session_state.economy

# --- INTRO ---
st.title("🏛️ Equilibrium: Agent-Based Economic Simulator")

st.markdown("""
<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px;'>
    <h3>🧪 Digital Economics Lab</h3>
    <p>Test policies like UBI, progressive taxes, and market crashes!</p>
    <ol>
        <li>Adjust policies in <strong>sidebar</strong></li>
        <li>Click <strong>Run Turn</strong> to simulate</li>
        <li>Watch <strong>Gini coefficient</strong> change</li>
        <li>Try <strong>Black Swan</strong> for market crash</li>
    </ol>
</div>
""", unsafe_allow_html=True)

# --- CONTROLS ---
col1, col2, col3 = st.columns(3)

policy_config = {
    'ubi': ubi_enabled,
    'ubi_amount': ubi_amount if ubi_enabled else 0.0,
    'transaction_cost': transaction_cost,
    'tax_rate': tax_rate if tax_enabled else 0.0,
    'inheritance_tax': inheritance_tax if inheritance_enabled else 0.0
}

with col1:
    if st.button("▶️ Run Next Turn", use_container_width=True):
        economy.run_turn(policy_config)
        st.rerun()

with col2:
    if st.button("🌑 Trigger Black Swan", use_container_width=True):
        economy.trigger_black_swan(impact=0.3)
        st.rerun()

with col3:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.economy = Economy(n_agents, grid_size)
        st.rerun()

# --- METRICS ---
st.divider()
wealths = [a.wealth for a in economy.agents]
current_gini = calculate_gini(wealths)
avg_wealth = np.mean(wealths)
bankrupt_count = sum(1 for w in wealths if w <= 0)

m1, m2, m3 = st.columns(3)
m1.metric("Turn", economy.turn)
m2.metric("Gini (Inequality)", f"{current_gini:.4f}")
m3.metric("Avg Wealth", f"${avg_wealth:,.0f}")

# --- CHARTS ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("📈 Gini Over Time")
    if len(economy.data_log) > 0:
        df = pd.DataFrame(economy.data_log)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(df['turn'], df['gini'], 'b-', linewidth=2, label='Gini')
        ax.set_xlabel("Turn")
        ax.set_ylabel("Gini Coefficient")
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        ax.legend()
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("👈 Run some turns first!")

with c2:
    st.subheader("📊 Lorenz Curve")
    if sum(wealths) > 0:
        cum_pop, cum_wealth = generate_lorenz_data(wealths)
        fig, ax = plt.subplots(figsize=(8, 5))
        x_data = np.concatenate([[0], cum_pop])
        y_data = np.concatenate([[0], cum_wealth])
        ax.plot(x_data, y_data, 'b-', linewidth=3, label='Actual')
        ax.plot([0,1], [0,1], 'r--', linewidth=2, label='Equality')
        ax.fill_between(x_data, y_data, x_data, alpha=0.3, color='blue')
        ax.set_xlabel("Cumulative Population %")
        ax.set_ylabel("Cumulative Wealth %")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.warning("No data yet!")

# --- AGENTS ---
st.subheader("👥 Agents")
col_a1, col_a2 = st.columns(2)

with col_a1:
    types = [a.type for a in economy.agents]
    type_counts = pd.Series(types).value_counts()
    fig, ax = plt.subplots(figsize=(6, 6))
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    ax.pie(type_counts.values, labels=type_counts.index, 
           autopct='%1.1f%%', colors=colors[:len(type_counts)])
    ax.set_title("Agent Types")
    st.pyplot(fig)
    plt.close(fig)

with col_a2:
    total = len(wealths)
    active = total - bankrupt_count
    st.metric("Active", active)
    st.metric("Bankrupt", bankrupt_count)
    st.progress(active/total)

# --- DATA ---
with st.expander("📋 Data Log"):
    if economy.data_log:
        st.dataframe(pd.DataFrame(economy.data_log).tail(20))