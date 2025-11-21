"use client";

import { useState, useRef, useEffect } from 'react';
import { Send, ThumbsUp, ThumbsDown, Loader2 } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  feedbackGiven?: boolean;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [modelAlias, setModelAlias] = useState('meta-llama/Llama-3.1-8B-Instruct/MyAssistant');
  const [isLoading, setIsLoading] = useState(false);
  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [currentFeedbackIndex, setCurrentFeedbackIndex] = useState<number | null>(null);
  const [correctionInput, setCorrectionInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: modelAlias,
          messages: [...messages, userMsg]
        })
      });

      const data = await response.json();
      if (data.error) {
          throw new Error(data.error);
      }

      const botMsg: Message = {
          role: 'assistant',
          content: data.choices[0].message.content
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (e: any) {
      console.error(e);
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = async (index: number, type: 'positive' | 'negative') => {
      if (type === 'positive') {
          // Send immediately
          await sendFeedbackAPI(index, 'positive');
      } else {
          // Open modal
          setCurrentFeedbackIndex(index);
          setFeedbackModalOpen(true);
          setCorrectionInput('');
      }
  };

  const sendFeedbackAPI = async (index: number, type: 'positive' | 'negative', correction?: string) => {
      const botMsg = messages[index];
      const userMsg = messages[index - 1]; // Assuming user msg is immediately before

      if (!userMsg || userMsg.role !== 'user') {
          console.error("Could not find corresponding user message");
          return;
      }

      try {
          const res = await fetch('/api/feedback', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  model_alias: modelAlias,
                  prompt: userMsg.content,
                  generated_output: botMsg.content,
                  feedback_type: type,
                  correct_output: correction
              })
          });
          const data = await res.json();
          if (data.success) {
              // Mark message as feedback given
              setMessages(prev => prev.map((m, i) => i === index ? { ...m, feedbackGiven: true } : m));
              alert("Feedback received! Model updated.");
          } else {
              alert("Error sending feedback: " + data.error);
          }
      } catch (e: any) {
          alert("Error: " + e.message);
      }
  };

  const submitCorrection = async () => {
      if (currentFeedbackIndex === null) return;
      await sendFeedbackAPI(currentFeedbackIndex, 'negative', correctionInput);
      setFeedbackModalOpen(false);
      setCurrentFeedbackIndex(null);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <h1 className="text-xl font-bold">Tinker Self-Improving Chat</h1>
        <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400">Model Alias:</label>
            <input
                type="text"
                value={modelAlias}
                onChange={(e) => setModelAlias(e.target.value)}
                className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm w-64"
            />
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-3 ${msg.role === 'user' ? 'bg-blue-600' : 'bg-gray-700'}`}>
              <div className="whitespace-pre-wrap">{msg.content}</div>

              {msg.role === 'assistant' && !msg.feedbackGiven && (
                  <div className="mt-2 flex gap-2 justify-end border-t border-gray-600 pt-2">
                      <button
                        onClick={() => handleFeedback(idx, 'positive')}
                        className="p-1 hover:bg-gray-600 rounded text-green-400"
                        title="Good response"
                      >
                          <ThumbsUp size={16} />
                      </button>
                      <button
                        onClick={() => handleFeedback(idx, 'negative')}
                        className="p-1 hover:bg-gray-600 rounded text-red-400"
                        title="Bad response (Provide correction)"
                      >
                          <ThumbsDown size={16} />
                      </button>
                  </div>
              )}
              {msg.role === 'assistant' && msg.feedbackGiven && (
                  <div className="mt-2 text-xs text-gray-400 text-right italic">
                      Feedback submitted
                  </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-700 bg-gray-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1 bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center disabled:opacity-50"
          >
            {isLoading ? <Loader2 className="animate-spin" /> : <Send />}
          </button>
        </div>
      </div>

      {/* Feedback Modal */}
      {feedbackModalOpen && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
              <div className="bg-gray-800 p-6 rounded-lg w-96">
                  <h2 className="text-lg font-bold mb-4">Provide Correction</h2>
                  <p className="text-sm text-gray-400 mb-2">What was the expected output?</p>
                  <textarea
                    value={correctionInput}
                    onChange={(e) => setCorrectionInput(e.target.value)}
                    className="w-full h-32 bg-gray-700 border border-gray-600 rounded p-2 mb-4 text-sm"
                    placeholder="Enter the correct response..."
                  />
                  <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setFeedbackModalOpen(false)}
                        className="px-4 py-2 bg-gray-600 hover:bg-gray-500 rounded text-sm"
                      >
                          Cancel
                      </button>
                      <button
                        onClick={submitCorrection}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm"
                      >
                          Submit & Train
                      </button>
                  </div>
              </div>
          </div>
      )}
    </div>
  );
}
