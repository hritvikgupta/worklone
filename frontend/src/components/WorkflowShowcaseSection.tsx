import React, { useState } from 'react';
import { motion } from 'motion/react';

const features = [
  {
    title: 'Coordinate AI employee chats',
    description:
      'Keep teams aligned with concurrent execution, unified context, and clear handoffs.',
    image: '/card2.png',
  },
  {
    title: 'Manage agent sprints',
    description:
      'View active sprint execution, move tasks across stages, and coordinate multiple AI employees from the same board.',
    image: '/card1.png',
  },
  {
    title: 'Build teams and assign workstreams',
    description:
      'Create a team with multiple employees, assign distinct tasks to each one, and track how work progresses across the full workflow.',
    image: '/card3.png',
  },
  {
    title: 'Train each employee with custom skills',
    description:
      'Manage every employee agent with its own skill set and training so each role performs with the right context and operating standards.',
    image: '/card4.png',
  },
];

export function WorkflowShowcaseSection() {
  const [activeIndex, setActiveIndex] = useState(0);
  const active = features[activeIndex];

  return (
    <section className="bg-white px-6 py-16 sm:px-8 sm:py-20 lg:px-10">
      <div className="mx-auto grid w-full max-w-7xl gap-10 lg:grid-cols-[0.92fr_1.08fr] lg:items-start lg:gap-14">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.45 }}
          className="flex flex-col gap-14 pt-6 sm:pt-8"
        >
          <h2 className="max-w-[620px] text-[32px] sm:text-[40px] font-medium leading-[1.15] tracking-tight text-zinc-950">
            Assign work and train employees inside your workspace
          </h2>

          <div className="flex flex-col gap-8">
            {features.map((feature, index) => {
              const isActive = index === activeIndex;
              return (
                <button
                  key={feature.title}
                  onClick={() => setActiveIndex(index)}
                  className="block text-left"
                >
                  <h3
                    className={`text-[24px] sm:text-[30px] font-normal leading-[1.15] tracking-tight transition-colors ${isActive ? 'text-zinc-900' : 'text-zinc-400 hover:text-zinc-600'}`}
                    style={{ fontWeight: 400 }}
                  >
                    {feature.title}
                  </h3>
                  {isActive && (
                    <p className="mt-4 max-w-[560px] text-[15px] leading-7 text-zinc-600">
                      {feature.description}
                    </p>
                  )}
                </button>
              );
            })}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.45, delay: 0.08 }}
          className="relative overflow-hidden rounded-[22px] border border-zinc-200 bg-[#f5f5f4]"
        >
          <div className="absolute bottom-0 right-0 top-10 left-10 overflow-hidden rounded-tl-[16px] border-t border-l border-zinc-200 bg-white shadow-[0_14px_30px_rgba(24,24,27,0.12)]">
            <motion.img
              key={active.image}
              src={active.image}
              alt={`${active.title} preview`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25 }}
              className="w-full h-auto object-top"
            />
          </div>
          <div className="h-[640px]" />
        </motion.div>
      </div>
    </section>
  );
}
