import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Layout } from './components/Layout';
import { TaskTable } from './components/TaskTable';
import { TemplateManager } from './components/TemplateManager';
import { CreateTaskModal } from './components/CreateTaskModal';
import { ParticleBackground } from './components/ui/ParticleBackground';
import { Button } from './components/ui/Button';
import { ConfirmModal } from './components/ui/ConfirmModal';
import { taskService, type Task } from './services/api';
import { ChevronLeft, ChevronRight, RotateCw } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'tasks' | 'templates'>('tasks');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [deleteTask, setDeleteTask] = useState<{ id: string; filename: string } | null>(null);

  // Task State
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  const loadTasks = useCallback(async (pageNum = 1) => {
    setIsLoading(true);
    try {
      const data = await taskService.getTasks(pageNum);
      setTasks(data.data.list || []);
      setTotalPages(data.data.total_pages);
      setTotal(data.data.total);
      setPage(data.data.page);
    } catch (err) {
      console.error('Failed to load tasks', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial load and auto-refresh
  useEffect(() => {
    if (activeTab === 'tasks') {
      loadTasks(page);
      const interval = setInterval(() => {
        // Silent refresh
        taskService.getTasks(page).then(data => {
          setTasks(data.data.list || []);
          setTotalPages(data.data.total_pages);
          setTotal(data.data.total);
        }).catch(console.error);
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [activeTab, page, loadTasks]);

  const handleDeleteClick = (id: string, filename: string) => {
    setDeleteTask({ id, filename });
  };

  const handleConfirmDelete = async () => {
    if (!deleteTask) return;
    try {
      await taskService.deleteTask(deleteTask.id);
      loadTasks();
    } catch (err) {
      console.error('Failed to delete task', err);
    } finally {
      setDeleteTask(null);
    }
  };

  return (
    <>
      <ParticleBackground />
      <Layout
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onCreateTask={() => setIsCreateModalOpen(true)}
      >
        <AnimatePresence mode="wait">
          {activeTab === 'tasks' ? (
            <motion.div
              key="tasks"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Tasks ({total})</h2>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<RotateCw size={14} />}
                  onClick={() => loadTasks(page)}
                  isLoading={isLoading}
                >
                  Refresh
                </Button>
              </div>

              <TaskTable
                tasks={tasks}
                isLoading={isLoading && tasks.length === 0}
                onDelete={handleDeleteClick}
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
                    Prev
                  </Button>
                  <span style={{ color: 'var(--color-text-secondary)' }}>
                    Page {page} of {totalPages}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage(p => p + 1)}
                    icon={<ChevronRight size={14} />}
                  >
                    Next
                  </Button>
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="templates"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <TemplateManager />
            </motion.div>
          )}
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
        title="Delete Task"
        message={`Delete task "${deleteTask?.filename}"?`}
        confirmText="Delete"
        cancelText="Cancel"
      />
    </>
  );
}

export default App;
