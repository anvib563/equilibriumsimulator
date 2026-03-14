import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import random

# ==========================================
# 1. THE MATH: Gini Coefficient & Analytics
# ==========================================

def calculate_gini(wealth_list):
    """Calculates the Gini Coefficient (0 = perfect equality, 1 = perfect inequality)."""
    wealth = np.array(wealth_list)
    if len(wealth) == 0 or np.sum(wealth) == 0:
        return 0.0
    
    sorted_wealth = np.sort(wealth)
    n = len(sorted_wealth)
    index = np.arange(1, n + 1)
    
    gini = (2 * np.sum(index * sorted_wealth)) / (n * np.sum(sorted_wealth)) - (n + 1) / n
    return round(gini, 4)

def generate_lorenz_data(wealth_list):
    """Prepares data for the Lorenz Curve."""
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
# 4. THE DASHBOARD: Streamlit UI (PLOTLY VERSION)
# ==========================================

st.set_page_config(page_title="Equilibrium Simulator", layout="wide")

# --- Initialize session state ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.economy = None
    st.session_state.last_n_agents = 100
    st.session_state.last_grid_size = 10

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Policy & Parameters")

n_agents = st.sidebar.slider("Number of Agents", 50, 500, 100)
grid_size = st.sidebar.slider("Grid Size", 5, 20, 10)
transaction_cost = st.sidebar.slider("Transaction Cost (%)", 0.0, 5.0, 0.1, 0.1)

st.sidebar.subheader("Government Policy")
ubi_enabled = st.sidebar.checkbox("Universal Basic Income", value=False)
ubi_amount = st.sidebar.number_input("UBI Amount/Turn", 0.0, 100.0, 1.0)

tax_enabled = st.sidebar.checkbox("Progressive Tax", value=False)
tax_rate = st.sidebar.slider("Tax Rate on Top 5%", 0.0, 0.5, 0.1)

inheritance_enabled = st.sidebar.checkbox("Inheritance Tax", value=False)
inheritance_tax = st.sidebar.slider("Inheritance Tax Rate", 0.0, 0.5, 0.2)

# --- Economy Management ---
if st.session_state.economy is None or \
   n_agents != st.session_state.last_n_agents or \
   grid_size != st.session_state.last_grid_size:
    
    st.session_state.economy = Economy(n_agents=n_agents, grid_size=grid_size)
    st.session_state.last_n_agents = n_agents
    st.session_state.last_grid_size = grid_size

economy = st.session_state.economy

# --- Title & Instructions ---
st.title("🏛️ Equilibrium: Agent-Based Economic Simulator")

st.markdown("""
**Digital Economics Lab** - Test policies like UBI, taxes, and market crashes on 100+ agents trading wealth.
""")

# --- Controls ---
col1, col2, col3 = st.columns(3)
policy_config = {
    'ubi': ubi_enabled, 'ubi_amount': ubi_amount,
    'transaction_cost': transaction_cost/100,
    'tax_rate': tax_rate if tax_enabled else 0,
    'inheritance_tax': inheritance_tax if inheritance_enabled else 0
}

with col1:
    if st.button("▶️ Run Turn", use_container_width=True):
        economy.run_turn(policy_config)
        st.rerun()

with col2:
    if st.button("🌑 Black Swan Event", use_container_width=True):
        economy.trigger_black_swan()
        st.rerun()

with col3:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.economy = Economy(n_agents, grid_size)
        st.rerun()

# --- Metrics ---
st.divider()
wealths = [a.wealth for a in economy.agents]
gini = calculate_gini(wealths)
bankrupt = sum(1 for w in wealths if w <= 0)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Turn", economy.turn)
col2.metric("Gini", f"{gini:.3f}", delta=None, help="0=equal, 1=unequal")
col3.metric("Avg Wealth", f"${np.mean(wealths):,.0f}")
col4.metric("Bankrupt", f"{bankrupt}/{len(wealths)}")

# --- Charts (PLOTLY - NO WARNINGS!) ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("📈 Gini Over Time")
    if economy.data_log:
        df = pd.DataFrame(economy.data_log)
        fig = px.line(df, x='turn', y='gini', 
                     title="Inequality Evolution",
                     labels={'gini': 'Gini Coefficient', 'turn': 'Turn'})
        fig.update_layout(height=400, showlegend=False, 
                         yaxis_range=[0,1], template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("📊 Lorenz Curve")
    if sum(wealths) > 0:
        cum_pop, cum_wealth = generate_lorenz_data(wealths)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=np.concatenate([[0], cum_pop]), 
                                y=np.concatenate([[0], cum_wealth]),
                                mode='lines', name='Actual',
                                line=dict(color='blue', width=3)))
        fig.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines',
                                name='Equality', line=dict(color='red', dash='dash')))
        fig.update_layout(height=400, showlegend=True,
                         xaxis_title="Population %", yaxis_title="Wealth %",
                         template='plotly_white')
        st.plotly_chart(fig, use_container_width=True)

# --- Agent Pie Chart ---
st.subheader("👥 Population")
col1, col2 = st.columns(2)

with col1:
    types = [a.type for a in economy.agents]
    type_df = pd.DataFrame({'type': types}).value_counts().reset_index()
    fig = px.pie(type_df, values='count', names='type', 
                title="Agent Types", hole=0.4)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col2:
    active = len(wealths) - bankrupt
    st.metric("Active Agents", active, delta=f"-{bankrupt}")
    st.progress(active / len(wealths))

# --- Data Table ---
with st.expander("📋 Recent Data", expanded=False):
    if economy.data_log:
        st.dataframe(pd.DataFrame(economy.data_log).tail(20))