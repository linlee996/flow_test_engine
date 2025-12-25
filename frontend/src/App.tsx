import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Layout } from './components/Layout';
import { TaskTable } from './components/TaskTable';
import { TemplateManager } from './components/TemplateManager';
import { LLMConfigManager } from './components/LLMConfigManager';
import { CreateTaskModal } from './components/CreateTaskModal';
import { ParticleBackground } from './components/ui/ParticleBackground';
import { Button } from './components/ui/Button';
import { ConfirmModal } from './components/ui/ConfirmModal';
import { Login } from './pages/Login';
import { taskService, type Task } from './services/api';
import { ChevronLeft, ChevronRight, RotateCw } from 'lucide-react';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [activeTab, setActiveTab] = useState<'tasks' | 'templates' | 'llm'>('tasks');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [deleteTask, setDeleteTask] = useState<{ id: number; filename: string } | null>(null);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 10;

  useEffect(() => {
    const token = localStorage.getItem('token');
    const savedUsername = localStorage.getItem('username');
    if (token && savedUsername) {
      setIsAuthenticated(true);
      setUsername(savedUsername);
    }
  }, []);

  const handleLoginSuccess = (token: string, username: string) => {
    localStorage.setItem('token', token);
    localStorage.setItem('username', username);
    setIsAuthenticated(true);
    setUsername(username);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setIsAuthenticated(false);
    setUsername('');
  };

  const loadTasks = useCallback(async (pageNum = 1) => {
    setIsLoading(true);
    try {
      const data = await taskService.getTasks(pageNum, pageSize);
      setTasks(data.tasks || []);
      setTotal(data.total);
      setPage(pageNum);
    } catch (err) {
      console.error('Failed to load tasks', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && activeTab === 'tasks') {
      loadTasks(page);
      const interval = setInterval(() => {
        taskService.getTasks(page, pageSize).then(data => {
          setTasks(data.tasks || []);
          setTotal(data.total);
        }).catch(console.error);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated, activeTab, page, loadTasks]);

  const handleDeleteClick = (id: number, filename: string) => {
    setDeleteTask({ id, filename });
  };

  const handleConfirmDelete = async () => {
    if (!deleteTask) return;
    try {
      await taskService.deleteTask(deleteTask.id);
      loadTasks(page);
    } catch (err) {
      console.error('Failed to delete task', err);
    } finally {
      setDeleteTask(null);
    }
  };

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  const totalPages = Math.ceil(total / pageSize);

  const renderContent = () => {
    switch (activeTab) {
      case 'tasks':
        return (
          <motion.div
            key="tasks"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 600 }}>任务列表 ({total})</h2>
              <Button
                variant="secondary"
                size="sm"
                icon={<RotateCw size={14} />}
                onClick={() => loadTasks(page)}
                isLoading={isLoading}
              >
                刷新
              </Button>
            </div>

            <TaskTable
              tasks={tasks}
              isLoading={isLoading && tasks.length === 0}
              onDelete={handleDeleteClick}
              onRefresh={() => loadTasks(page)}
            />

            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', alignItems: 'center' }}>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                  icon={<ChevronLeft size={14} />}
                >
                  上一页
                </Button>
                <span style={{ color: 'var(--color-text-secondary)' }}>
                  第 {page} 页 / 共 {totalPages} 页
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => p + 1)}
                  icon={<ChevronRight size={14} />}
                >
                  下一页
                </Button>
              </div>
            )}
          </motion.div>
        );
      case 'templates':
        return (
          <motion.div
            key="templates"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <TemplateManager />
          </motion.div>
        );
      case 'llm':
        return (
          <motion.div
            key="llm"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <LLMConfigManager />
          </motion.div>
        );
    }
  };

  return (
    <>
      <ParticleBackground />
      <Layout
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onCreateTask={() => setIsCreateModalOpen(true)}
        username={username}
        onLogout={handleLogout}
      >
        <AnimatePresence mode="wait">
          {renderContent()}
        </AnimatePresence>
      </Layout>
      <CreateTaskModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          setActiveTab('tasks');
          loadTasks(1);
        }}
      />

      <ConfirmModal
        isOpen={!!deleteTask}
        onClose={() => setDeleteTask(null)}
        onConfirm={handleConfirmDelete}
        title="删除任务"
        message={`确定要删除任务 "${deleteTask?.filename}" 吗？`}
        confirmText="删除"
        cancelText="取消"
      />
    </>
  );
}

export default App;
