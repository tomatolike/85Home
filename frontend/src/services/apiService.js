import axios from 'axios';

class ApiService {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  async fetchStatus() {
    try {
      const response = await this.client.get('/status');
      return response.data.statuses;
    } catch (error) {
      console.error('Failed to fetch status:', error);
      throw error;
    }
  }

  async sendTask(task) {
    try {
      const response = await this.client.post('/task', task);
      return response.data;
    } catch (error) {
      console.error('Failed to send task:', error);
      throw error;
    }
  }
}

export default ApiService;
