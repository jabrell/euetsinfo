# Institutional Background

## European Emissions Trading System
The EU ETS regulates the greenhouse gas emissions of energy and energy intense industries,
air, and maritime transport. To manage both the environmental compliance and the market trading of these emissions, it helps to think in two layers — a physical layer of installations and a trading layer of accounts — bridged by the account holders that connect them to the real-world entities outside the system:

![Overview of the EU Transaction Log: inside the system boundary sit the person
holding, operator holding and administrative accounts that exchange allowances
through transactions, each linked to an account holder; the operator holding
account represents an installation, while the account holders bridge across the
EUTL boundary to the real-world companies and regulatory authorities outside
it.](../figures/eutl_overview.svg)

The figure above gives an overview of how these pieces fit together: the EU
Transaction Log (EUTL) is the boxed system in the middle, the accounts and
installation live inside it, and account holders form the bridge to the
real-world companies and regulatory authorities outside the box. The rest of this
section explains each part in turn.

**The Physical and Regulatory Layer: Installations**
Installations are the actual regulated entities within the EU ETS. All emission accounting takes place strictly at the installation level. Each year, these installations carry the regulatory obligation to surrender allowances equal to their verified emissions from the previous year. Installations
receive allowances by either acquiring them from the market or by free allocation.

**The Trading Layer: Accounts**
While emissions are tracked at the installation level, the actual transfer of allowances (transactions) takes place entirely between accounts. To interact with the market, each installation is represented by an **Operator Holding Account (OHA)**, which allows it to receive, transfer, and surrender allowances.
Because the EU ETS is an open market, non-regulated actors (such as financial intermediaries) can also participate in trading using **Person Holding Accounts (PHA)**. Regulatory authorities participate using **Administrative Accounts (AA)** to issue allocations and receive surrendered allowances.

**The Bridge: Account Holders**
Real-world companies and regulatory bodies are not directly represented within the EUTL database.
Instead, every account is assigned a primary contact known as the **Account Holder**.
These Account Holders serve as the vital link across the boundary of the EUTL, connecting external legal entities (like parent companies) to their respective trading accounts inside the system.
