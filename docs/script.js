class StatsDashboard {
    constructor() {
        this.statsData = [];
        this.dataUrl = 'https://raw.githubusercontent.com/ThatSINEWAVE/SINEWAVE-Development-Statistics/refs/heads/main/statistics/server_stats.json';
        this.charts = {};
        this.updateInterval = 300000; // 5 minutes

        this.init();
    }

    async init() {
        await this.loadData();
        this.initCharts();
        this.updateDashboard();
        this.startAutoRefresh();
    }

    async loadData() {
        try {
            const timestamp = new Date().getTime();
            const response = await fetch(`${this.dataUrl}?t=${timestamp}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.statsData = data.stats || [];

            console.log(`Loaded ${this.statsData.length} data points`);
        } catch (error) {
            console.error('Error loading data:', error);
            // Fallback to sample data if fetch fails
            this.statsData = this.getSampleData();
        }
    }

    getSampleData() {
        // Sample data structure matching your JSON format
        return [{
                "total_members": 215,
                "online_members": 35,
                "messages_per_hour": 12,
                "timestamp": new Date(Date.now() - 10 * 60000).toISOString()
            },
            {
                "total_members": 215,
                "online_members": 34,
                "messages_per_hour": 8,
                "timestamp": new Date(Date.now() - 5 * 60000).toISOString()
            },
            {
                "total_members": 215,
                "online_members": 35,
                "messages_per_hour": 15,
                "timestamp": new Date().toISOString()
            }
        ];
    }

    getCurrentStats() {
        if (this.statsData.length === 0) return null;
        return this.statsData[this.statsData.length - 1];
    }

    getPreviousStats() {
        if (this.statsData.length < 2) return null;
        return this.statsData[this.statsData.length - 2];
    }

    calculateChange(current, previous) {
        if (!previous || previous === 0) return {
            change: 0,
            percentage: 0
        };
        const change = current - previous;
        const percentage = ((change / previous) * 100).toFixed(1);
        return {
            change,
            percentage
        };
    }

    formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }

    calculateActivityLevel(onlineMembers, totalMembers, messagesPerHour) {
        const onlineRatio = onlineMembers / totalMembers;
        const messageScore = Math.min(messagesPerHour / 20, 1); // Normalize message count
        const activityScore = (onlineRatio * 0.7 + messageScore * 0.3) * 100;

        if (activityScore >= 50) return 'High';
        if (activityScore >= 25) return 'Medium';
        return 'Low';
    }

    updateCurrentStats() {
        const current = this.getCurrentStats();
        const previous = this.getPreviousStats();

        if (!current) return;

        // Update total members
        const totalEl = document.getElementById('totalMembers');
        totalEl.textContent = this.formatNumber(current.total_members);
        totalEl.classList.add('pulse');

        if (previous) {
            const change = this.calculateChange(current.total_members, previous.total_members);
            const changeEl = document.getElementById('totalMembersChange');
            this.updateChangeElement(changeEl, change, 'members');
        }

        // Update online members
        const onlineEl = document.getElementById('onlineMembers');
        onlineEl.textContent = this.formatNumber(current.online_members);
        onlineEl.classList.add('pulse');

        if (previous) {
            const change = this.calculateChange(current.online_members, previous.online_members);
            const changeEl = document.getElementById('onlineMembersChange');
            this.updateChangeElement(changeEl, change, 'online');
        }

        // Update messages per hour
        const messagesEl = document.getElementById('messagesPerHour');
        messagesEl.textContent = this.formatNumber(current.messages_per_hour);
        messagesEl.classList.add('pulse');

        if (previous) {
            const change = this.calculateChange(current.messages_per_hour, previous.messages_per_hour);
            const changeEl = document.getElementById('messagesChange');
            this.updateChangeElement(changeEl, change, 'messages');
        }

        // Update activity level
        const activityLevel = this.calculateActivityLevel(
            current.online_members,
            current.total_members,
            current.messages_per_hour
        );
        const activityEl = document.getElementById('activityLevel');
        activityEl.textContent = activityLevel;
        activityEl.className = 'stat-value ' +
            (activityLevel === 'High' ? 'status-high' :
                activityLevel === 'Medium' ? 'status-medium' : 'status-low');
        activityEl.classList.add('pulse');

        // Update last updated time
        document.getElementById('lastUpdated').textContent =
            `Last updated: ${this.formatTimestamp(current.timestamp)}`;

        // Remove pulse animation after delay
        setTimeout(() => {
            [totalEl, onlineEl, messagesEl, activityEl].forEach(el => {
                if (el) el.classList.remove('pulse');
            });
        }, 500);
    }

    updateChangeElement(element, change, type) {
        if (!element) return;

        const sign = change.change > 0 ? '+' : '';
        const arrow = change.change > 0 ? '↑' : change.change < 0 ? '↓' : '→';

        element.textContent = `${arrow} ${sign}${change.change} (${sign}${change.percentage}%)`;
        element.className = 'stat-change ' +
            (change.change > 0 ? 'positive' : change.change < 0 ? 'negative' : 'neutral');
    }

    initCharts() {
        this.initMembersChart();
        this.initMessagesChart();
        this.initActivityChart();
    }

    initMembersChart() {
        const ctx = document.getElementById('membersChart').getContext('2d');

        this.charts.members = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                        label: 'Total Members',
                        data: [],
                        borderColor: '#4361ee',
                        backgroundColor: 'rgba(67, 97, 238, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#4361ee',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Online Members',
                        data: [],
                        borderColor: '#4cc9f0',
                        backgroundColor: 'rgba(76, 201, 240, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#4cc9f0',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#a0a0a0',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#4361ee',
                        borderWidth: 1,
                        cornerRadius: 6
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(45, 45, 45, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0a0a0'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(45, 45, 45, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0a0a0'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                animations: {
                    tension: {
                        duration: 1000,
                        easing: 'linear'
                    }
                }
            }
        });
    }

    initMessagesChart() {
        const ctx = document.getElementById('messagesChart').getContext('2d');

        this.charts.messages = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Messages per Hour',
                    data: [],
                    backgroundColor: 'rgba(67, 97, 238, 0.7)',
                    borderColor: '#4361ee',
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#a0a0a0',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#4361ee',
                        borderWidth: 1,
                        cornerRadius: 6
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(45, 45, 45, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0a0a0'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(45, 45, 45, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0a0a0'
                        }
                    }
                },
                animations: {
                    tension: {
                        duration: 1000,
                        easing: 'linear'
                    }
                }
            }
        });
    }

    initActivityChart() {
        const ctx = document.getElementById('activityChart').getContext('2d');

        this.charts.activity = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                        label: 'Online Ratio (%)',
                        data: [],
                        borderColor: '#4ade80',
                        backgroundColor: 'rgba(74, 222, 128, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y',
                        pointBackgroundColor: '#4ade80',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    },
                    {
                        label: 'Message Activity',
                        data: [],
                        borderColor: '#4cc9f0',
                        backgroundColor: 'rgba(76, 201, 240, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1',
                        pointBackgroundColor: '#4cc9f0',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#a0a0a0',
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#4361ee',
                        borderWidth: 1,
                        cornerRadius: 6
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(45, 45, 45, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0a0a0'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: 'rgba(45, 45, 45, 0.5)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#a0a0a0'
                        },
                        title: {
                            display: true,
                            text: 'Online Ratio (%)',
                            color: '#a0a0a0'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            color: '#a0a0a0'
                        },
                        title: {
                            display: true,
                            text: 'Messages/Hour',
                            color: '#a0a0a0'
                        }
                    },
                },
                animations: {
                    tension: {
                        duration: 1000,
                        easing: 'linear'
                    }
                }
            }
        });
    }

    updateCharts() {
        if (this.statsData.length === 0) return;

        const labels = this.statsData.map(stat => {
            const date = new Date(stat.timestamp);
            return date.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
        });

        const totalMembers = this.statsData.map(stat => stat.total_members);
        const onlineMembers = this.statsData.map(stat => stat.online_members);
        const messages = this.statsData.map(stat => stat.messages_per_hour);
        const onlineRatios = this.statsData.map(stat =>
            ((stat.online_members / stat.total_members) * 100).toFixed(1)
        );

        // Update members chart
        if (this.charts.members) {
            this.charts.members.data.labels = labels;
            this.charts.members.data.datasets[0].data = totalMembers;
            this.charts.members.data.datasets[1].data = onlineMembers;
            this.charts.members.update();
        }

        // Update messages chart
        if (this.charts.messages) {
            this.charts.messages.data.labels = labels;
            this.charts.messages.data.datasets[0].data = messages;
            this.charts.messages.update();
        }

        // Update activity chart
        if (this.charts.activity) {
            this.charts.activity.data.labels = labels;
            this.charts.activity.data.datasets[0].data = onlineRatios;
            this.charts.activity.data.datasets[1].data = messages;
            this.charts.activity.update();
        }
    }

    updateDataTable() {
        const tbody = document.getElementById('statsTableBody');
        if (!tbody) return;

        // Show last 10 entries
        const recentStats = this.statsData.slice(-10).reverse();

        tbody.innerHTML = recentStats.map(stat => `
            <tr>
                <td>${this.formatTimestamp(stat.timestamp)}</td>
                <td>${this.formatNumber(stat.total_members)}</td>
                <td>${this.formatNumber(stat.online_members)}</td>
                <td>${this.formatNumber(stat.messages_per_hour)}</td>
                <td>${((stat.online_members / stat.total_members) * 100).toFixed(1)}%</td>
            </tr>
        `).join('');
    }

    updateDashboard() {
        this.updateCurrentStats();
        this.updateCharts();
        this.updateDataTable();
    }

    startAutoRefresh() {
        setInterval(async () => {
            await this.loadData();
            this.updateDashboard();
        }, this.updateInterval);
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new StatsDashboard();
});

// Add error handling for uncaught errors
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});