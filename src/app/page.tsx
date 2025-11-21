"use client";

import { useState, useEffect } from 'react';
import { Send, ThumbsUp, ThumbsDown, Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  metadata?: {
    modelAlias?: string;
    logprobs?: number[];
    tokens?: number[];
  };
  feedback?: 'positive' | 'negative';
}

interface Model {
  name: string;
}

export default function Home() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [baseModels, setBaseModels] = useState<string[]>([]);
  const [selectedBaseModel, setSelectedBaseModel] = useState('');
  const [customAlias, setCustomAlias] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Feedback Modal State
  const [showModal, setShowModal] = useState(false);
  const [correctOutput, setCorrectOutput] = useState('');
  const [feedbackMessageIndex, setFeedbackMessageIndex] = useState<number | null>(null);

  useEffect(() => {
    fetch('/api/models')
      .then(res => res.json())
      .then(data => {
        if (data.models) {
          setBaseModels(data.models);
          if (data.models.length > 0) setSelectedBaseModel(data.models[0]);
        }
      })
      .catch(err => console.error('Failed to fetch models:', err));
  }, []);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    // Construct Alias
    const modelAlias = customAlias
      ? `${selectedBaseModel}/${customAlias}`
      : selectedBaseModel;

    const newMessages: Message[] = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: modelAlias,
          messages: newMessages
        })
      });

      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.output,
        metadata: {
          modelAlias: modelAlias,
          logprobs: data.logprobs,
          tokens: data.tokens
        }
      }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error generating response.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = async (index: number, type: 'positive' | 'negative') => {
    if (type === 'negative') {
      setFeedbackMessageIndex(index);
      setShowModal(true);
    } else {
      // Positive feedback immediately
      await sendFeedback(index, 'positive');
    }
  };

  const sendFeedback = async (index: number, type: 'positive' | 'negative', correction?: string) => {
    const msg = messages[index];
    const userMsg = messages[index - 1]; // Assuming prev message is prompt

    if (!msg.metadata?.modelAlias) return;

    // Update UI
    const updatedMessages = [...messages];
    updatedMessages[index].feedback = type;
    setMessages(updatedMessages);

    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_alias: msg.metadata.modelAlias,
          prompt: userMsg.content,
          generated_output: msg.content,
          feedback_type: type,
          correct_output: correction,
          logprobs: msg.metadata.logprobs,
          tokens: msg.metadata.tokens
        })
      });
      // Ideally show toast success
    } catch (error) {
      console.error('Feedback error:', error);
    }
  };

  const submitCorrection = async () => {
    if (feedbackMessageIndex !== null) {
      await sendFeedback(feedbackMessageIndex, 'negative', correctOutput);
      setShowModal(false);
      setCorrectOutput('');
      setFeedbackMessageIndex(null);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center p-8 bg-gray-900 text-white font-sans">
      <div className="w-full max-w-4xl flex flex-col h-[90vh] bg-gray-800 rounded-xl shadow-2xl overflow-hidden">

        {/* Header / Model Selector */}
        <div className="p-4 bg-gray-950 border-b border-gray-700 flex flex-col md:flex-row gap-4 items-center justify-between">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Tinker Self-Improving API
          </h1>

          <div className="flex gap-2 items-center">
             <select
               className="bg-gray-800 border border-gray-600 rounded p-2 text-sm"
               value={selectedBaseModel}
               onChange={(e) => setSelectedBaseModel(e.target.value)}
             >
               {baseModels.map(m => <option key={m} value={m}>{m}</option>)}
             </select>
             <span className="text-gray-500">/</span>
             <input
               type="text"
               placeholder="Specific-Task-Name"
               className="bg-gray-800 border border-gray-600 rounded p-2 text-sm w-40"
               value={customAlias}
               onChange={(e) => setCustomAlias(e.target.value)}
             />
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={cn(
              "flex w-full gap-4",
              msg.role === 'user' ? "justify-end" : "justify-start"
            )}>
              <div className={cn(
                "max-w-[80%] p-4 rounded-2xl",
                msg.role === 'user'
                  ? "bg-blue-600 rounded-tr-none"
                  : "bg-gray-700 rounded-tl-none"
              )}>
                <div className="flex items-center gap-2 mb-1 opacity-50 text-xs">
                  {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                  <span>{msg.role === 'user' ? 'You' : (msg.metadata?.modelAlias || 'Assistant')}</span>
                </div>
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Feedback Controls for Assistant */}
                {msg.role === 'assistant' && !msg.feedback && (
                  <div className="flex gap-2 mt-3 justify-end border-t border-gray-600 pt-2">
                    <button
                      onClick={() => handleFeedback(idx, 'positive')}
                      className="p-1 hover:text-green-400 transition-colors"
                    >
                      <ThumbsUp size={16} />
                    </button>
                    <button
                      onClick={() => handleFeedback(idx, 'negative')}
                      className="p-1 hover:text-red-400 transition-colors"
                    >
                      <ThumbsDown size={16} />
                    </button>
                  </div>
                )}

                {msg.feedback && (
                  <div className="mt-2 text-xs text-right opacity-60">
                    {msg.feedback === 'positive' ? 'Feedback: Positive' : 'Feedback: Negative (Corrected)'}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
             <div className="flex justify-start w-full animate-pulse">
               <div className="bg-gray-700 rounded-2xl rounded-tl-none p-4 h-12 w-24"></div>
             </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 bg-gray-950 border-t border-gray-700">
          <div className="relative">
            <input
              type="text"
              className="w-full bg-gray-800 border border-gray-600 rounded-full py-3 px-5 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              disabled={isLoading}
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-blue-600 rounded-full hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Correction Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-xl w-full max-w-md shadow-2xl border border-gray-700">
            <h2 className="text-lg font-bold mb-4">Help Improve the Model</h2>
            <p className="text-sm text-gray-300 mb-4">
              What was the expected correct answer? (Just the answer, we will synthesize the reasoning).
            </p>
            <textarea
              className="w-full bg-gray-900 border border-gray-600 rounded p-3 min-h-[100px] focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="The correct answer is..."
              value={correctOutput}
              onChange={(e) => setCorrectOutput(e.target.value)}
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={submitCorrection}
                className="px-4 py-2 text-sm bg-blue-600 rounded hover:bg-blue-500"
              >
                Submit Correction
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
